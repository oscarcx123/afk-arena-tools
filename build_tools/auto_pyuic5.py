import os

def get_ui_file():
    ui_file_list = []
    file_list = os.listdir()
    for filename in file_list:
        if os.path.splitext(filename)[1] == ".ui":
            ui_file_list.append(filename)
    return ui_file_list

def pyuic_convert(ui_file_list):
    for filename in ui_file_list:
        name = os.path.splitext(filename)[0]
        os.system(f"pyuic5 -o {name}.py {name}.ui")
        print(f"{name}.ui -> {name}.py")

if __name__ == "__main__":
     ui_file_list = get_ui_file()
     pyuic_convert(ui_file_list)
