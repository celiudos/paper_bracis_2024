import re

# pylint: disable=import-error
from utils.ModeloNerBase import (
    ModeloNerBase,
)


class ModeloNerUtils(ModeloNerBase):
    def __init__(
        self,
        transformer=None,
        remover_labels=[
            "MISC",
            "LOCATION",
            "LOC",
            "ORGANIZACAO",
            "LEGISLACAO",
            "TEMPO",
            "NUMERO",
        ],
        merges={
            "NOME": ["PESSOA", "PERSON", "PER"],
            "DATA": ["DATE", "DATA", "DATE_TIME"],
            "ENDERECO": ["LOCAL"],
            "EMAIL": ["EMAIL_ADDRESS"],
            "TELEFONE": ["PHONE_NUMBER"],
            "DINHEIRO": ["MONEY"],
        },
    ):
        self.transformer = transformer
        self.regex_temos_sensiveis = None
        self.remover_labels = remover_labels
        self.merges = merges

    def convert_promptnotation_to_transformer(self, text, labels):
        entities = []

        if type(labels) == str:  # noqa: E721
            labels = eval(labels)

        for label_name, terms in labels.items():
            if type(terms) == str:  # noqa: E721
                terms = list(
                    terms.replace("[", "").replace("]", "").replace("'", "").split(", ")
                )
            for term in terms:
                matches = re.finditer(r"(" + re.escape(term) + ")", text)

                for match in matches:
                    start = match.start()
                    end = match.end()
                    entity = {
                        "entity_group": label_name,
                        "word": term.strip(),
                        "start": start,
                        "end": end,
                    }
                    entities.append(entity)
        return entities

    def convert_transformer_to_gradio(self, text):
        ents = self.transformer(text)  # type: ignore

        i = 0
        while i < len(ents) - 1:
            se_final_da_anterior_igual_ao_inicio_da_proxima = (
                ents[i]["end"] == ents[i + 1]["start"]
            )
            se_final_da_anterior_igual_ao_inicio_da_proxima_mais_1 = (
                ents[i]["end"] == ents[i + 1]["start"] - 1
            )
            if (
                se_final_da_anterior_igual_ao_inicio_da_proxima
                or se_final_da_anterior_igual_ao_inicio_da_proxima_mais_1
            ):
                ents[i]["end"] = ents[i + 1]["end"]
                ents[i]["word"] = f"{ents[i]['word']} {ents[i+1]['word']}"
                ents.pop(i + 1)
            else:
                i += 1
        return ents

    def convert_regex_to_gradio(self, text, regex_terms=[]):
        entities = []
        for tipo, pattern in regex_terms.items():
            try:
                matches = re.finditer(pattern, text, re.IGNORECASE)

                for match in matches:
                    start = match.start()
                    end = match.end()
                    entity = {
                        "entity_group": tipo,
                        "word": text[start:end].strip(),
                        "start": start,
                        "end": end,
                    }
                    entities.append(entity)
            except Exception as e:
                # print warning
                print("Erro ao converter Regex: ", tipo, e)
                pass

        return entities

    def get_regex(self):
        return {
            "CEP": r"\b\d{5}-?\d{3}\b",
            # "CEP": r"\b\d{5}-\d{3}\b",
            "CPF": r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",
            "CNPJ": r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b",
            "DATA": r"\b\d{2}/\d{2}/\d{4}\b",
            "TELEFONE": r"\+?\d?\d??\s?\(?\d{2,3}\)?\s?\d{3,4}[-\s]?\d{4}",
            "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "DINHEIRO": r"\b(?:R\$)?\s?\d{1,3}(?:.\d{3})*\,\d{2}|(?:R\$)\s?\d{1,3}\b",
            "URL": r"\b(?:https?)?://\S+|www\.\S+\b",
            "NUMERO": r"\b(?<=[Nn][º°]\s)(?:\d|\.)*\b",
        }

    def set_regex_temos_sensiveis(self, label_termo="", lista_termos=[]):
        if self.regex_temos_sensiveis is None:
            self.regex_temos_sensiveis = {}

        self.regex_temos_sensiveis[label_termo] = "|".join(lista_termos)
        return self.regex_temos_sensiveis

    def merge_labels_from_to(self, ents, merges={}):
        ents_n = self.merge_labels_from_transformer(ents, merges)
        return ents_n

    def merge_all_models(self, text):
        out1 = self.convert_transformer_to_gradio(text)
        out2 = self.convert_regex_to_gradio(text, self.get_regex())
        out3 = []
        if self.regex_temos_sensiveis:
            out3 = self.convert_regex_to_gradio(text, self.regex_temos_sensiveis)
        out_merged_entities = out1 + out2 + out3
        return out_merged_entities

    def remove_labels(self, ents, remover_labels=[]):
        new_ent = []
        for ent in ents:
            ent_g = ent["entity_group"]
            if ent_g not in remover_labels:
                new_ent += [ent]

        return new_ent

    def merge_labels_from_transformer(self, ents, merges):
        for final_label, possibles_labels in merges.items():
            for p in possibles_labels:
                for ent in ents:
                    ent_g = ent["entity_group"]
                    if p == ent_g:
                        ent["entity_group"] = final_label

        return ents

    def convert_ents_into_presidio_format(self, text, ents):
        entity_groups = {}
        entity_count = {}
        output_text = text

        for ent in ents:
            entity_group = ent["entity_group"]
            word = ent["word"]

            if entity_group not in entity_groups:
                entity_groups[entity_group] = {}
                entity_count[entity_group] = 1
            else:
                entity_count[entity_group] += 1

            if entity_count[entity_group] == 1:
                entity_placeholder = f"<{entity_group}>"
            else:
                entity_placeholder = f"<{entity_group}_{entity_count[entity_group]}>"

            if word not in entity_groups[entity_group].values():
                entity_groups[entity_group][entity_placeholder] = word

            output_text = output_text.replace(word, entity_placeholder)

        return output_text, entity_groups

    def run(
        self,
        text,
        remover_labels=[],
        merges={},
    ):
        if len(remover_labels) == 0:
            remover_labels = self.remover_labels

        if len(merges) == 0:
            merges = self.merges

        ents = self.merge_all_models(text)
        # ents = self.convert_gradio_to_generic(text, ents)
        ents = self.remove_labels(ents, remover_labels)

        ents = self.merge_labels_from_to(ents, merges)
        # ents = self.merge_values_from_to(ents)

        texto_anonimizado, segredo_de_anonimizacao = (
            self.convert_ents_into_presidio_format(text, ents)
        )

        entidades_gradio = self.convert_output_presidio_to_gradio_highlight(
            texto_anonimizado, segredo_de_anonimizacao
        )

        return texto_anonimizado, segredo_de_anonimizacao, entidades_gradio

    def convert_run_to_tokens_and_inputs_ids(
        self,
        text,
        label2id=[],
        remover_labels=["MISC", "LOCATION", "LOC", "ORGANIZACAO"],
        merges={
            "LEGISLACAO": ["LAW"],
            "NOME": ["PESSOA", "PERSON", "PER"],
            "TEMPO": ["DATE", "DATA", "DATE_TIME"],
            "EMAIL": ["EMAIL_ADDRESS"],
            "TELEFONE": ["PHONE_NUMBER"],
            "DINHEIRO": ["MONEY"],
        },
    ):
        tokens = text.split(" ")

        ents = self.merge_all_models(text)
        ents = self.remove_labels(ents, remover_labels)
        ents = self.merge_labels_from_to(ents, merges)

        inputs_ids = []

        for i, token in enumerate(tokens):
            is_achou_token = False
            for e in ents:
                # start = e["start"]
                # end = e["end"]
                entity = e["entity_group"]
                word = e["word"]

                if token in word and len(token) > 1:
                    inputs_ids.append(label2id[entity])
                    is_achou_token = True
                    break

            if not is_achou_token:
                is_achou_token = False
                inputs_ids.append(0)

        return {"text": text, "tokens": tokens, "inputs_ids": inputs_ids}
