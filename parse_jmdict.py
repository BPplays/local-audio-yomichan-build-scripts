"""
Generates jmdict_forms.json
"""

import json
from collections import defaultdict
from typing import TypedDict, NotRequired
import xml.etree.ElementTree as ET

JMDICT_PATH = 'temp/JMdict_e'
OUTPUT_JSON = "output/jmdict_forms.json"


KATAKANA_CHART = "ァアィイゥウェエォオカガカ゚キギキ゚クグク゚ケゲケ゚コゴコ゚サザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶヽヾ"
HIRAGANA_CHART = "ぁあぃいぅうぇえぉおかがか゚きぎき゚くぐく゚けげけ゚こごこ゚さざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをんゔゕゖゝゞ"
KATA2HIRA = str.maketrans(KATAKANA_CHART, HIRAGANA_CHART)
HIRA2KATA = str.maketrans(HIRAGANA_CHART, KATAKANA_CHART)


def katakana_to_hiragana(kana):
    return kana.translate(KATA2HIRA)


def eletostr(ele):
    return ET.tostring(ele, encoding="utf8").decode('utf-8', 'ignore')


class KanjiInfo(TypedDict):
    kanji: str
    override_reading: NotRequired[str]


def get_readings_to_kanji(ele, filter_non_plural=True):
    # reb: reading
    # r_ele: contains reb and potentially r_kanji

    readings_to_kanji = defaultdict(list)

    for r_ele in ele.findall("r_ele"):
        # ASSUMPTION: this reb is a kana reading unique to this element
        reb = r_ele.find("reb")

        re_restr_list = r_ele.findall("re_restr")
        if re_restr_list:
            for re_restr in re_restr_list:
                expr = re_restr.text
                kanji_info: KanjiInfo = {
                    "kanji": expr,
                }
                readings_to_kanji[reb.text].append(kanji_info)
        elif r_ele.find("re_nokanji") is not None:
            # this is apparently how yomichan searches for text
            # i.e. &term=ウオジラミ&reading=ウオジラミ
            # we group it with the hiragana form for valid searches
            kanji_info: KanjiInfo = {
                "kanji": reb.text,
                "override_reading": reb.text,
            }
            readings_to_kanji[katakana_to_hiragana(reb.text)].append(kanji_info)
        else:
            # in the absense of re_restr, all of k_ele/keb is used
            for keb in ele.findall("k_ele/keb"):
                kanji_info: KanjiInfo = {
                    "kanji": keb.text,
                }
                readings_to_kanji[reb.text].append(kanji_info)

        # TODO: should we do anything if the word is uk / "usually kana"?

    if filter_non_plural:
        filtered = {}
        for k, v in readings_to_kanji.items():
            if len(v) > 1:
                filtered[k] = v
    else:
        filtered = readings_to_kanji

    # filters into groups, i.e. {"reading": reading, expressions: []}
    result = []
    for k, v in filtered.items():
        result_pair = {
            "reading": k,
            "expressions": v
        }
        result.append(result_pair)
    return result

def main():
    tree = ET.parse(JMDICT_PATH)
    root = tree.getroot()
    result = []
    for ele in root:
        result.extend(get_readings_to_kanji(ele))
    with open(OUTPUT_JSON, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

    #from pprint import pprint

    #tree = ET.parse(JMDICT_PATH)
    #root = tree.getroot()

    ## usually kana, contains re_restr
    #e = root.find("entry/k_ele/keb[.='魚虱']/../..")
    #pprint(get_readings_to_kanji(e))

    ## 言葉典
    #e = root.find("entry/ent_seq[.='2855054']/..")
    #pprint(get_readings_to_kanji(e))

    ## only kana
    #e = root.find("entry/ent_seq[.='1012320']/..") # むかつく
    #pprint(get_readings_to_kanji(e))

    ## normal entry
    #e = root.find("entry/ent_seq[.='2038970']/..") # 不審者
    #pprint(get_readings_to_kanji(e))


