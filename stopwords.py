class StopWords:
    def __init__(self, filename):
        self.filename = filename

        self.__load()

    def __load(self):
        try:
            f = open(self.filename, 'r')
        except FileNotFoundError:
            open(self.filename, 'w').close()
            self.words = set()
        else:
            words = f.read().split(';')
            self.words = set(words)

    def __save(self):
        with open(self.filename, 'w') as f:
            for word in self.words:
                f.write(word + ';')

    def add(self, word):
        self.words.add(word)
        self.__save()

    def word_status(self, word):
        if word in self.words:
            return True
        else:
            return False
