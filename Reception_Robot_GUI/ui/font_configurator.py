# ui/font_configurator.py

from ui.fonts import set_bold, set_regular

def apply_custom_fonts(ui):
    #thanh cong cu - login
    set_bold(ui.label_mqtt)
    set_bold(ui.label_battery)

    #dashboard_login - login
    set_regular(ui.Signin_btn_signup)
    set_regular(ui.Signin_btn_signin)
    set_bold(ui.Signin_text)
    
    #page_signin - login 
    set_bold(ui.label_2)
    set_regular(ui.label_4)
    set_regular(ui.Signin_username)
    set_regular(ui.Signin_password)
    set_regular(ui.Signin_btn_login)

    #page_signup - login 
    set_bold(ui.label_9)
    set_regular(ui.Signup_name)
    set_regular(ui.Signup_code)
    set_regular(ui.Signup_password)
    set_regular(ui.Signup_phone)
    set_regular(ui.Signup_username)
    set_regular(ui.Signup_btn_signup)

    #thanh cong cu - robot 
    set_bold(ui.label_mqtt_3)
    set_bold(ui.label_battery_3)
    set_bold(ui.comboBox_2)

    #page_attendance - robot 
    set_regular(ui.label_22)
    set_regular(ui.label_15)
    set_regular(ui.label_16)
    set_regular(ui.label_17)
    set_bold(ui.table_attendance_2)

    #page_control - robot 
    set_bold(ui.label_14)
    set_regular(ui.label1_4)
    set_bold(ui.robot_status)
    set_regular(ui.label1_5)
    set_bold(ui.label_left_2)
    set_bold(ui.label_right_2)
    set_regular(ui.label1_6)
    set_bold(ui.label_xy_2)
    set_bold(ui.label_theta_2)
    set_bold(ui.mode_select_2)
    set_bold(ui.label_log)
    set_bold(ui.label_25)
    set_bold(ui.btn_goal_A)
    set_bold(ui.btn_goal_B)
    set_bold(ui.btn_goal_C)
    set_bold(ui.btn_goal_D)
    set_bold(ui.btn_goal_E)
    set_bold(ui.btn_goal_F)
    set_bold(ui.btn_goal_G)
    set_bold(ui.btn_goal_H)
    set_bold(ui.btn_goal_I)

    #page_guest2 - robot 
    set_regular(ui.label1_11)
    set_bold(ui.label_xy_3)
    set_bold(ui.label_theta_3)
    set_regular(ui.label1_12)
    set_bold(ui.label_left_3)
    set_bold(ui.label_right_3)
    set_regular(ui.label1_13)
    set_bold(ui.robot_status_2)


    #thanh cong cu - guest 
    set_bold(ui.label_mqtt_4)
    set_bold(ui.label_battery_4)
    #page - guest 
    set_regular(ui.label1_10)
    set_bold(ui.label_xy)
    set_bold(ui.label_theta)
    set_regular(ui.label1_9)
    set_bold(ui.label_left)
    set_bold(ui.label_right)