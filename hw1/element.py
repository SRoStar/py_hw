class Element:
    def __init__(self, name, number, weight):
        self.name = name
        self.number = number
        self.weight = weight
        self.melting_point = None
        self.boiling_point = None
        self.crust = None
        self.meteor = None
        self.ocean = None
        self.solar = None
        self.universe = None
        self.discover = None
        self.compound = []

    def print(self):
        print("name = " + self.name)
        print("number = " + self.number)
        print("weight = " + self.weight)
        print("melting_point = " + self.melting_point)
        print("boiling_point = " + self.boiling_point)
        print("crust = " + self.crust)
        print("meteor = " + self.meteor)
        print("ocean = " + self.ocean)
        print("solar = " + self.solar)
        print("universe = " + self.universe)
        print("discover = " + self.discover)
