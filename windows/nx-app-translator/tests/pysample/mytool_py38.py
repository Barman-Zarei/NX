import sys

def classify(n):
    if n is None:
        return "none"
    if n == 0:
        return "zero"
    return "num:" + str(n)

def main():
    name = "prefix-demo"
    if name.startswith("prefix-"):
        name = name[len("prefix-"):]
    print("mytool", name, classify(0), classify(7), classify(None))
    return 0

if __name__ == "__main__":
    sys.exit(main())
