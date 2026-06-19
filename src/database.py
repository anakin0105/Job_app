"""Модуль PostgreSQL для курсовой — чистая версия без скрытых символов."""

import time
import os
from typing import List, Tuple
import psycopg2
from dotenv import load_dotenv
from src.api import Hh_handler
from src.vacancies import Vacancy

load_dotenv(override=True, encoding="utf-8")



# Без dotenv — прямые значения
DB_NAME = "Job"
DB_USER = "postgres"
DB_PASSWORD = "Anna2301"
DB_HOST = "127.0.0.1"
DB_PORT = "5432"

print("=== DEBUG ===")
print(f"DB_NAME = '{DB_NAME}'")
print(f"DB_USER = '{DB_USER}'")
print(f"DB_HOST = '{DB_HOST}'")
print("=============\n")


def create_database() -> None:
    try:
        conn = psycopg2.connect(dbname="postgres", user=DB_USER, password=DB_PASSWORD,
                                host=DB_HOST, port=DB_PORT)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"✅ База '{DB_NAME}' создана")
        else:
            print(f"✅ База '{DB_NAME}' уже существует")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Ошибка создания базы: {e}")


def create_tables() -> None:
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
                                host=DB_HOST, port=DB_PORT)
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS employers (
            id SERIAL PRIMARY KEY,
            hh_id VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL
        );""")
        cur.execute("""CREATE TABLE IF NOT EXISTS vacancies (
            id SERIAL PRIMARY KEY,
            hh_id VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            salary_from INTEGER,
            salary_to INTEGER,
            currency VARCHAR(10),
            url TEXT,
            requirement TEXT,
            responsibility TEXT,
            employer_id INTEGER REFERENCES employers(id) ON DELETE CASCADE
        );""")
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Таблицы созданы")
    except Exception as e:
        print(f"⚠️ Ошибка создания таблиц: {e}")


def fill_database() -> None:
    print("🚀 Запускаем заполнение базы данных...")
    hh = Hh_handler()
    db = DBManager()

    companies = ["Яндекс", "Сбер", "Тинькофф", "VK", "Ozon", "Wildberries",
                 "Avito", "МТС", "Газпром нефть", "Росатом"]

    for name in companies:
        try:
            print(f"\n📌 Ищем компанию: {name}")

            # 1. Ищем вакансии компании
            resp = hh.get("https://api.hh.ru/vacancies", {
                "text": name,
                "per_page": 1,
                "employer_id": None  # на всякий случай
            })

            items = resp.json().get("items", [])
            if not items:
                print(f"   ⚠️ Вакансий по {name} не найдено")
                continue

            vacancy = items[0]
            employer = vacancy.get("employer", {})
            employer_hh_id = employer.get("id")
            employer_name = employer.get("name") or name

            if not employer_hh_id:
                print(f"   ⚠️ Не удалось получить employer_id для {name}")
                continue

            emp_id = db.add_employer(employer_hh_id, employer_name)

            # 2. Получаем вакансии этой компании
            vacs = hh.get_vacancies(
                params={"employer_id": employer_hh_id},
                num=30,  # чуть больше, но не 100
                verbal=False
            )

            added = 0
            for v in vacs:
                try:
                    vac = Vacancy(v)
                    db.add_vacancy(vac.to_dict(), emp_id)
                    added += 1
                except Exception as e:
                    continue

            print(f"   ✅ {employer_name}: добавлено {added} вакансий")

            time.sleep(2)  # ← Очень важно! HH.ru не любит частые запросы

        except Exception as e:
            print(f"   ❌ Проблема с {name}: {e}")
            time.sleep(5)

    print("🎉 Заполнение завершено!\n")


class DBManager:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                connect_timeout=10
            )
            self.cur = self.conn.cursor()
            print("✅ Подключение к PostgreSQL успешно!")
        except Exception as e:
            print(f"❌ Ошибка подключения: {type(e).__name__} — {e}")
            raise

    def __del__(self):
        if hasattr(self, 'cur') and self.cur: self.cur.close()
        if hasattr(self, 'conn') and self.conn: self.conn.close()

    # 5 методов по ТЗ (оставил самые важные)
    def get_companies_and_vacancies_count(self):
        self.cur.execute("SELECT e.name, COUNT(v.id) FROM employers e LEFT JOIN vacancies v ON e.id = v.employer_id GROUP BY e.name ORDER BY COUNT(v.id) DESC;")
        return self.cur.fetchall()

    def get_all_vacancies(self):
        self.cur.execute("SELECT e.name, v.name, v.salary_from, v.salary_to, v.currency, v.url FROM vacancies v JOIN employers e ON v.employer_id = e.id ORDER BY e.name;")
        return self.cur.fetchall()

    def get_avg_salary(self):
        self.cur.execute("SELECT ROUND(AVG((COALESCE(salary_from,0)+COALESCE(salary_to,0))/2.0),2) FROM vacancies WHERE salary_from>0 OR salary_to>0;")
        res = self.cur.fetchone()[0]
        return res if res else 0.0

    def get_vacancies_with_higher_salary(self):
        self.cur.execute("""SELECT e.name, v.name, v.salary_from, v.salary_to, v.currency, v.url 
                            FROM vacancies v JOIN employers e ON v.employer_id = e.id 
                            WHERE (COALESCE(v.salary_from,0)+COALESCE(v.salary_to,0))/2.0 > 
                                  (SELECT AVG((COALESCE(salary_from,0)+COALESCE(salary_to,0))/2.0) FROM vacancies 
                                   WHERE salary_from>0 OR salary_to>0);""")
        return self.cur.fetchall()

    def get_vacancies_with_keyword(self, keyword: str):
        self.cur.execute("""SELECT e.name, v.name, v.salary_from, v.salary_to, v.currency, v.url 
                            FROM vacancies v JOIN employers e ON v.employer_id = e.id 
                            WHERE v.name ILIKE %s ORDER BY e.name;""", (f"%{keyword}%",))
        return self.cur.fetchall()

    def add_employer(self, hh_id: str, name: str) -> int:
        self.cur.execute("INSERT INTO employers (hh_id, name) VALUES (%s,%s) ON CONFLICT (hh_id) DO UPDATE SET name=EXCLUDED.name RETURNING id;", (hh_id, name))
        self.conn.commit()
        return self.cur.fetchone()[0]

    def add_vacancy(self, vac_dict: dict, employer_id: int):
        self.cur.execute("""INSERT INTO vacancies 
            (hh_id, name, salary_from, salary_to, currency, url, requirement, responsibility, employer_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (hh_id) DO NOTHING;""",
            (vac_dict["id"], vac_dict["name"], vac_dict.get("salary_from"), vac_dict.get("salary_to"),
             vac_dict.get("currency"), vac_dict.get("url"), vac_dict.get("requirement"),
             vac_dict.get("responsibility"), employer_id))
        self.conn.commit()