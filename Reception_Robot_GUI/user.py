from PyQt6.QtWidgets import QMessageBox
from ui.style import show_custom_dialog

def handle_login(ui, registered_users, main_window):
    username = ui.Signin_username.text()
    password = ui.Signin_password.text()

    for user in registered_users:
        if user["username"] == username and user["password"] == password:
            return True  # Thành công
    show_custom_dialog("Login Failed", "Incorrect username or password", main_window=main_window)
    return False

def handle_signup(ui, registered_users, main_window):
    fullname = ui.Signup_name.text()
    phone = ui.Signup_phone.text()
    username = ui.Signup_username.text()
    password = ui.Signup_password.text()
    verify = ui.Signup_code.text()

    if not all([fullname, phone, username, password, verify]):
        show_custom_dialog("Sign Up Failed", "Please fill in all fields", main_window=main_window)
        return False

    if verify.strip().lower() != "fablab":
        show_custom_dialog("Sign Up Failed", "Incorrect verification code", main_window=main_window)
        return False

    for user in registered_users:
        if user["username"] == username:
            show_custom_dialog("Sign Up Failed", "Username already exists", main_window=main_window)
            return False

    registered_users.append({
        "fullname": fullname,
        "phone": phone,
        "username": username,
        "password": password,
        "verify": verify
    })
    show_custom_dialog("Success", "Account created successfully", main_window=main_window)
    return True