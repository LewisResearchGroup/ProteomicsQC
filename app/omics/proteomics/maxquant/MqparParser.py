import re


class MqparParser:
    """Parser for mqpar.xml files"""

    def __init__(self, filename=None, as_template=False):
        self._content = None

        if filename is not None:
            self.read(filename)

        if as_template:
            self.as_template()

    def read(self, filename):
        self._filename = filename
        with open(filename, "r") as file:
            self._content = "".join(file.readlines())
        return self

    def print(self):
        print(self._content)

    def as_template(self):
        new_content = self._content

        repls = {
            "<fastaFilePath>.*</fastaFilePath>": "<fastaFilePath>__FASTA__</fastaFilePath>",
            "<string>.*.[raw,RAW]</string>": "<string>__RAW__</string>",
        }

        for pattern, repl in repls.items():
            new_content = re.sub(pattern, repl, new_content)

        n_raws = len(re.findall("__RAW__", new_content))
        assert n_raws == 1, Exception("Please use mqpar.xml for single RAW file.")
        self._content = new_content
        return self

    def write(self, filename=None):
        if filename is None:
            filename = self._filename
        with open(filename, "w") as file:
            file.write(self._content)
