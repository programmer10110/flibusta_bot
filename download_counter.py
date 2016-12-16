import json


class Counter:
    def __init__(self, filename):
        self.filename = filename
        self.__load(filename)

    def __load(self, filename):
        try:
            open(filename, 'r')
        except IOError:
            self.counters = {}
        else:
            json_str = open(filename, 'r', encoding='utf-8').read()
            if json_str:
                self.counters = json.loads(json_str)
            else:
                self.counters = {}

    def __save(self):
        with open(self.filename, 'w') as f:
            json.dump(self.counters, f, sort_keys=True, indent=4)

    def add(self, _id):
        if self.counters.get(_id):
            self.counters[_id] += 1
        else:
            self.counters[_id] = 1
        self.__save()

    def get(self, _id):
        count = self.counters.get(_id)
        if count:
            return count
        else:
            return 0
