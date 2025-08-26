# FastAPI Diary Project

## 📌 프로젝트 소개

FastAPI 기반의 일기 관리 웹 서비스

- 기능: 회원가입/로그인/로그아웃, JWT 인증, 일기 CRUD, 검색 및 정렬, 감정 분석

- 기술 스택: FastAPI, Pydantic, PostgreSQL, Docker, Aerich, JWT

---

## 📂 프로젝트 구조

```plaintext
app/
 ├── diary/
 │   ├── api.py
 │   ├── service.py
 │   ├── repository.py
 │   ├── schema.py
 │   ├── model.py
 │   ├── test_diary.py
 │   └── __init__.py
 ├── user/
 │   ├── api.py
 │   ├── service.py
 │   ├── repository.py
 │   ├── schema.py
 │   ├── model.py
 │   ├── test_user.py
 │   └── __init__.py
 ├── tag/
 │   ├── api.py
 │   ├── service.py
 │   ├── repository.py
 │   ├── schema.py
 │   ├── model.py
 │   ├── test_tag.py
 │   └── __init__.py
 ├── core/              # 공통
 ├── db/
 └── main.py
```
