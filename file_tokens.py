import json


class FileTokens:
    def __init__(self, filename):
        self.filename = filename
        self.__load(filename)

    def __load(self, filename):
        try:
            open(filename, 'r')
        except IOError:
            self.tokens = {}
        else:
            json_str = open(filename, 'r').read()
            if json_str:
                self.tokens = json.loads(open(filename, 'r').read())
            else:
                self.tokens = {}

    def __save(self):
        with open(self.filename, 'w') as f:
            json.dump(self.tokens, f, sort_keys=True, indent=4)

    def add(self, _id, _type, token):
        if self.tokens.get(_id):
            self.tokens[_id].update({_type: token})
        else:
            self.tokens[_id] = {_type: token}
        self.__save()

    def get(self, _id, _type):
        if self.tokens.get(_id):
            if self.tokens[_id].get(_type):
                return self.tokens[_id][_type]
            else:
                return None
        else:
            return None
