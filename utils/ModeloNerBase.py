import re


class ModeloNerBase:
    def plain_output_json(self, dicionario):
        resultado = {}
        for _, valor in dicionario.items():
            for subchave, subvalor in valor.items():
                resultado[subchave] = subvalor
        return resultado

    def convert_output_presidio_to_gradio_highlight(self, text="", out_map={}):
        plain_json = self.plain_output_json(out_map)
        new_dict = {"text": text, "entities": []}
        regex_get_label = r"(?<=<)[A-Z]+(?=(?:>|_))"

        for tag_label in plain_json.keys():
            if tag_label in text:
                label_name = re.findall(regex_get_label, tag_label)[0]

                for match in re.finditer(tag_label, text):
                    new_dict["entities"].append(
                        {
                            "entity_group": label_name,
                            "word": tag_label,
                            "start": match.start(),
                            "end": match.end(),
                        }
                    )
        return new_dict

    def merge_labels(self, ents, merges):
        for k, v in merges.items():
            if k in ents:
                for label in v:
                    if label in ents:
                        ents[k] += ents[label]
                        del ents[label]

        return ents

    def agroup_entities(self, ents):
        i = 0
        while i < len(ents) - 1:
            if ents[i]["end"] == ents[i + 1]["start"]:
                ents[i]["end"] = ents[i + 1]["end"]
                ents[i]["word"] = f"{ents[i]['word']} {ents[i+1]['word']}"
                ents.pop(i + 1)
            else:
                i += 1
        return ents

    def convert_gradio_to_generic(self, text, ents):
        ents_alt = []
        for ent in ents:
            ent["label"] = ent.pop("entity_group")
            ents_alt.append(ent)

        ents_final = self.agroup_entities(ents_alt)
        words = [(ent["label"], text[ent["start"] : ent["end"]]) for ent in ents_final]
        words_dict = {}
        for _, w in enumerate(words):
            key_word = w[0]
            value_word = w[1]
            if key_word not in words_dict:
                words_dict[key_word] = []
            if value_word not in words_dict[key_word]:
                words_dict[key_word].append(value_word)
        return words_dict
