import dataclasses
import re
from pathlib import Path

import requests

import consts


@dataclasses.dataclass
class QualityData:
    key: str
    value_per_quality: float
    translation: str
    index_handles: list[str]


@dataclasses.dataclass
class Gem:
    idx: str
    name: str
    qualities: [QualityData] = None

    def __init__(self, idx, name, raw_quality, translations):
        self.idx = idx
        self.name = name
        self.qualities = self._parse_qualities(raw_quality, translations)

    @staticmethod
    def create_quality_data(key, value, translations):
        raw_translation = ""
        index_handlers = []

        value_per_level = float(value)
        matching_translations = [t for t in translations if key in t['ids']]
        if len(matching_translations) > 0:
            max_quality_val = 20 * value_per_level
            matching_translation = matching_translations[0]
            variants = [variant for variant in matching_translation['English']]
            matched = False
            for variant in variants:
                for condition in variant['condition']:
                    if condition.get('min') and condition.get('min') <= max_quality_val:
                        matched = True
                if matched or not any(variant['condition']):
                    raw_translation = variant['string']
                    index_handlers = variant['index_handlers']

        return QualityData(key, float(value), raw_translation, index_handlers)

    @staticmethod
    def _parse_qualities(raw_quality, translations):
        regex = r"\w*\W=\W{.*?\"(.*?)\",\W+(.*?)\W}"
        return [Gem.create_quality_data(key, value, translations) for key, value in
                re.findall(regex, raw_quality, re.MULTILINE | re.DOTALL)]


def parse_gem_quality(url, translations: dict):
    resp = requests.get(url)
    if resp.status_code == 200:
        content = resp.text
        regex = r"skills\[(.*?)\].*?name\W+?\"(.*?)\".*?qualityStats\W*\{(.*?)stats"
        return [Gem(idx, name, qualities, translations) for idx, name, qualities in
                re.findall(regex, content, re.MULTILINE | re.DOTALL)]


def fetch_translations(url):
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()


def prep_gem_table(gems):
    html = """<table>
  <thead>
    <tr>
      <th scope="col">Idx</th>
      <th scope="col">Name</th>
      <th scope="col">Qualities</th>
    </tr>
  </thead>
  <tbody>"""

    for gem in gems:
        html += f"""
        <tr>
          <td>{gem.idx}</td>
          <td>{gem.name}</td>
          <td>
            <table>
              <tr>
                <th scope="col">Description</th>
                <th scope="col">Value per %</th>
                <th scope="col">Additional Info</th>
              </tr>
              """
        for quality in gem.qualities:
            html += f"""      
              <tr>
          
                  <td>{quality.translation}</td>
                  <td>{quality.value_per_quality}</td>
                  <td>{quality.index_handles}</td>
              </tr>
          """
        html += """</table>
          </td>

        </tr>
        """

    html += "</tbody>" \
                       "</table>"
    return html


def write_html(parsed_gems: {str, Gem}):
    dynamic_content = ""

    section_translation = {
        'active_dex': "Dexterity Skills",
        'active_int': "Intelligence Skills",
        'active_str': "Strength Skills",
        'support_dex': "Dexterity Supports",
        'support_int': "Intelligence Supports",
        'support_str': "Strength Supports"
    }
    for section, gems in parsed_gems.items():
        print(section, len(gems))
        dynamic_content += f"<h2>{section_translation.get(section)}</h2>"
        dynamic_content += prep_gem_table(gems)

    out = Path('index.html')
    out.write_text(f"""<!DOCTYPE html>
<html lang="">
<head>
    <title>POE Gem Quality</title>
    <link rel="stylesheet" href="css/pico.min.css">
</head>
<main class="container">
    <h1>POE Gem Quality Overview</h1>

    <main class="container">
        {dynamic_content}
    </main>
</main>
</body>
</html>
    """)


def main():
    translations = fetch_translations(consts.repoe_translations)
    gem_dict = {
        'active_dex': parse_gem_quality(consts.active_dex_gem, translations),
        'active_int': parse_gem_quality(consts.active_int_gem, translations),
        'active_str': parse_gem_quality(consts.active_str_gem, translations),
        'support_dex': parse_gem_quality(consts.support_dex_gem, translations),
        'support_int': parse_gem_quality(consts.support_int_gem, translations),
        'support_str': parse_gem_quality(consts.support_str_gem, translations)
    }

    write_html(gem_dict)


if __name__ == '__main__':
    main()
