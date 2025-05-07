# 🎓 LMSWebsite – Learning Management System (Web)

## 🌐 Overview

LMSWebsite is a simple web-based Learning Management System built using Django. It allows students and instructors to manage courses, assignments, and submissions, providing a centralized place for tracking academic progress and coursework online.

Designed for clarity and straightforward navigation, the LMSWebsite is ideal for small-scale educational setups or as a project demonstration of full-stack web development using Django.

## 🎯 Project Objectives

- Develop a fully functional web LMS for managing courses, assignments, and users.
- Implement user roles (e.g., student, instructor) with different permissions.
- Allow assignment creation, submission tracking, and grading workflows.
- Build clear and accessible front-end templates using Django’s templating system.

## 🛠️ Technologies Used

- **Languages:** Python
- **Frameworks:** Django
- **Frontend:** Django templates, HTML, CSS
- **Version Control:** Git, GitHub
- **IDE:** Visual Studio Code

## 🧠 Key Learnings

- **Django Models & Views:** Built clean models and views to represent core LMS features.
- **User Authentication:** Implemented login, registration, and permission control using Django’s built-in auth.
- **Form Handling:** Designed forms for assignment submission and grading.
- **CRUD Operations:** Enabled smooth create, read, update, and delete workflows across core entities.
- **Template Design:** Focused on building accessible, responsive pages using Django templates and Bootstrap.

## 🚀 Getting Started

1. **Clone the repository:**

    ```bash
    git clone https://github.com/landonwest815/LMSWebsite.git
    ```

2. **Run migrations and start the server:**

    ```bash
    python3 manage.py makemigrations
    rm db.sqlite3
    python3 manage.py migrate
    python3 makedata.py
    python manage.py runserver
    ```

4. **Access the app:**
    - Navigate to `http://127.0.0.1:8000/` in your browser.
    - Log in or create a user to start exploring the LMS features.
