import flet as ft

def main(page: ft.Page):
    page.title = "Hello"
    counter = ft.Text(0, size=40)
    
    def add_one(e):
        counter.value = str(int(counter.value) + 1)
    
    page.add(counter, ft.Button(content="add one", on_click=add_one))
    
ft.run(main)