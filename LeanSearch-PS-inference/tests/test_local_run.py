import conf.config
from worker import PremiseSelector

def local_run():
    premise_selector = PremiseSelector()
    related_theorems = premise_selector.retrieve(conf.config.TEST_QUERY, num=5)
    for theorems in related_theorems:
        for theorem in theorems:
            print(theorem)
            print("-" * 40)

if __name__ == '__main__':
    local_run()








