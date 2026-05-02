import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import os
from datetime import datetime
from threading import Thread


class GitHubUserFinder:
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub User Finder")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # Файл для хранения избранных
        self.favorites_file = "favorites.json"
        self.favorites = self.load_favorites()

        # Создание интерфейса
        self.setup_ui()

        # Кэш для результатов поиска
        self.current_results = []

    def setup_ui(self):
        # Стили
        style = ttk.Style()
        style.theme_use('clam')

        # Основной контейнер
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Настройка весов для растягивания
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Заголовок
        title_label = ttk.Label(main_frame, text="GitHub User Finder", font=('Arial', 18, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 20))

        # Поле поиска
        search_frame = ttk.Frame(main_frame)
        search_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        search_frame.columnconfigure(1, weight=1)

        ttk.Label(search_frame, text="Поиск пользователя:").grid(row=0, column=0, padx=(0, 10))

        self.search_entry = ttk.Entry(search_frame, font=('Arial', 11))
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.search_entry.bind('<Return>', lambda e: self.search_user())

        self.search_button = ttk.Button(search_frame, text="Найти", command=self.search_user)
        self.search_button.grid(row=0, column=2)

        # Разделитель
        ttk.Separator(main_frame, orient='horizontal').grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)

        # Панель с вкладками
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)

        # Вкладка результатов поиска
        self.results_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.results_frame, text="Результаты поиска")

        # Таблица результатов
        columns = ('avatar', 'username', 'name', 'followers', 'repos')
        self.results_tree = ttk.Treeview(self.results_frame, columns=columns, show='headings', height=15)

        # Настройка колонок
        self.results_tree.heading('avatar', text='')
        self.results_tree.heading('username', text='Логин')
        self.results_tree.heading('name', text='Имя')
        self.results_tree.heading('followers', text='Подписчики')
        self.results_tree.heading('repos', text='Репозитории')

        self.results_tree.column('avatar', width=30, stretch=False)
        self.results_tree.column('username', width=150)
        self.results_tree.column('name', width=200)
        self.results_tree.column('followers', width=80)
        self.results_tree.column('repos', width=80)

        # Скроллбар для таблицы
        vsb = ttk.Scrollbar(self.results_frame, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=vsb.set)

        self.results_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Контекстное меню для результатов
        self.results_menu = tk.Menu(self.results_tree, tearoff=0)
        self.results_menu.add_command(label="Добавить в избранное", command=self.add_to_favorites)
        self.results_menu.add_command(label="Показать профиль", command=self.show_profile)
        self.results_tree.bind("<Button-3>", self.show_results_menu)

        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)

        # Вкладка избранного
        self.favorites_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.favorites_frame, text="⭐ Избранное")

        # Таблица избранного
        self.favorites_tree = ttk.Treeview(self.favorites_frame, columns=columns, show='headings', height=15)

        self.favorites_tree.heading('avatar', text='')
        self.favorites_tree.heading('username', text='Логин')
        self.favorites_tree.heading('name', text='Имя')
        self.favorites_tree.heading('followers', text='Подписчики')
        self.favorites_tree.heading('repos', text='Репозитории')

        self.favorites_tree.column('avatar', width=30, stretch=False)
        self.favorites_tree.column('username', width=150)
        self.favorites_tree.column('name', width=200)
        self.favorites_tree.column('followers', width=80)
        self.favorites_tree.column('repos', width=80)

        vsb_fav = ttk.Scrollbar(self.favorites_frame, orient="vertical", command=self.favorites_tree.yview)
        self.favorites_tree.configure(yscrollcommand=vsb_fav.set)

        self.favorites_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb_fav.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Контекстное меню для избранного
        self.favorites_menu = tk.Menu(self.favorites_tree, tearoff=0)
        self.favorites_menu.add_command(label="Удалить из избранного", command=self.remove_from_favorites)
        self.favorites_menu.add_command(label="Показать профиль", command=self.show_profile)
        self.favorites_tree.bind("<Button-3>", self.show_favorites_menu)

        self.favorites_frame.columnconfigure(0, weight=1)
        self.favorites_frame.rowconfigure(0, weight=1)

        # Статусная строка
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к работе")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # Загрузка избранного в таблицу
        self.refresh_favorites_display()

    def load_favorites(self):
        """Загрузка избранных из JSON файла"""
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_favorites(self):
        """Сохранение избранных в JSON файл"""
        with open(self.favorites_file, 'w', encoding='utf-8') as f:
            json.dump(self.favorites, f, ensure_ascii=False, indent=2)

    def refresh_favorites_display(self):
        """Обновление отображения избранного"""
        # Очистка таблицы
        for item in self.favorites_tree.get_children():
            self.favorites_tree.delete(item)

        # Заполнение таблицы
        for username, data in self.favorites.items():
            self.favorites_tree.insert('', 'end', values=(
                '⭐',
                username,
                data.get('name', 'N/A'),
                data.get('followers', 0),
                data.get('public_repos', 0)
            ), tags=(username,))

    def search_user(self):
        """Поиск пользователя GitHub"""
        username = self.search_entry.get().strip()

        # Проверка корректности ввода
        if not username:
            messagebox.showwarning("Ошибка ввода", "Поле поиска не должно быть пустым!")
            self.status_var.set("Ошибка: поле поиска пустое")
            return

        # Блокировка кнопки во время запроса
        self.search_button.config(state='disabled', text='Поиск...')
        self.status_var.set(f"Поиск пользователя '{username}'...")

        # Запуск в отдельном потоке
        thread = Thread(target=self.fetch_user_data, args=(username,))
        thread.daemon = True
        thread.start()

    def fetch_user_data(self, username):
        """Получение данных пользователя из GitHub API"""
        try:
            url = f"https://api.github.com/users/{username}"
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'GitHubUserFinderApp'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                user_data = response.json()
                self.update_results_display(user_data)
                self.status_var.set(f"Пользователь '{username}' найден")
            elif response.status_code == 404:
                self.root.after(0, lambda: messagebox.showinfo("Не найдено",
                                                               f"Пользователь '{username}' не найден на GitHub"))
                self.status_var.set(f"Пользователь '{username}' не найден")
                self.root.after(0, self.clear_results)
            else:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка API: {response.status_code}"))
                self.status_var.set("Ошибка при выполнении запроса")

        except requests.exceptions.Timeout:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", "Превышено время ожидания ответа от сервера"))
            self.status_var.set("Ошибка: таймаут запроса")
        except requests.exceptions.ConnectionError:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", "Нет подключения к интернету"))
            self.status_var.set("Ошибка: нет подключения")
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Произошла ошибка: {str(e)}"))
            self.status_var.set("Произошла ошибка")
        finally:
            self.root.after(0, self.enable_search_button)

    def update_results_display(self, user_data):
        """Обновление отображения результатов поиска"""
        # Очистка таблицы
        self.clear_results()

        # Сохранение данных в кэш
        self.current_results = [user_data]

        # Вставка данных в таблицу
        self.results_tree.insert('', 'end', values=(
            '👤',
            user_data['login'],
            user_data.get('name', 'N/A'),
            user_data.get('followers', 0),
            user_data.get('public_repos', 0)
        ), tags=(user_data['login'],))

        # Переключение на вкладку результатов
        self.notebook.select(self.results_frame)

    def clear_results(self):
        """Очистка результатов поиска"""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.current_results = []

    def enable_search_button(self):
        """Включение кнопки поиска"""
        self.search_button.config(state='normal', text='Найти')

    def add_to_favorites(self):
        """Добавление пользователя в избранное"""
        selected = self.results_tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите пользователя для добавления в избранное")
            return

        # Получение данных выбранного пользователя
        values = self.results_tree.item(selected[0])['values']
        username = values[1]

        # Проверка, есть ли уже в избранном
        if username in self.favorites:
            messagebox.showinfo("Информация", f"Пользователь '{username}' уже в избранном")
            return

        # Поиск полных данных пользователя
        user_data = next((user for user in self.current_results if user['login'] == username), None)

        if user_data:
            self.favorites[username] = {
                'login': user_data['login'],
                'name': user_data.get('name', ''),
                'followers': user_data.get('followers', 0),
                'public_repos': user_data.get('public_repos', 0),
                'avatar_url': user_data.get('avatar_url', ''),
                'html_url': user_data.get('html_url', ''),
                'added_at': datetime.now().isoformat()
            }
            self.save_favorites()
            self.refresh_favorites_display()
            self.status_var.set(f"Пользователь '{username}' добавлен в избранное")
            messagebox.showinfo("Успех", f"Пользователь '{username}' добавлен в избранное")

    def remove_from_favorites(self):
        """Удаление пользователя из избранного"""
        selected = self.favorites_tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите пользователя для удаления из избранного")
            return

        values = self.favorites_tree.item(selected[0])['values']
        username = values[1]

        if messagebox.askyesno("Подтверждение", f"Удалить пользователя '{username}' из избранного?"):
            del self.favorites[username]
            self.save_favorites()
            self.refresh_favorites_display()
            self.status_var.set(f"Пользователь '{username}' удален из избранного")

    def show_results_menu(self, event):
        """Показ контекстного меню для результатов поиска"""
        item = self.results_tree.identify_row(event.y)
        if item:
            self.results_tree.selection_set(item)
            self.results_menu.post(event.x_root, event.y_root)

    def show_favorites_menu(self, event):
        """Показ контекстного меню для избранного"""
        item = self.favorites_tree.identify_row(event.y)
        if item:
            self.favorites_tree.selection_set(item)
            self.favorites_menu.post(event.x_root, event.y_root)

    def show_profile(self):
        """Открытие профиля пользователя в браузере"""
        # Определяем, на какой вкладке мы находимся
        current_tab = self.notebook.index(self.notebook.select())

        if current_tab == 0:  # Вкладка результатов
            selected = self.results_tree.selection()
            if not selected:
                return
            values = self.results_tree.item(selected[0])['values']
            username = values[1]

            # Поиск URL пользователя
            user_data = next((user for user in self.current_results if user['login'] == username), None)
            if user_data and 'html_url' in user_data:
                import webbrowser
                webbrowser.open(user_data['html_url'])
                self.status_var.set(f"Открыт профиль: {username}")

        elif current_tab == 1:  # Вкладка избранного
            selected = self.favorites_tree.selection()
            if not selected:
                return
            values = self.favorites_tree.item(selected[0])['values']
            username = values[1]

            if username in self.favorites and 'html_url' in self.favorites[username]:
                import webbrowser
                webbrowser.open(self.favorites[username]['html_url'])
                self.status_var.set(f"Открыт профиль: {username}")


def main():
    root = tk.Tk()
    app = GitHubUserFinder(root)
    root.mainloop()


if __name__ == "__main__":
    main()