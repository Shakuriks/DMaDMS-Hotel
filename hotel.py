import psycopg2
from datetime import datetime

def is_valid_date(date_string):
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False
    

def get_action_log(conn):
    query = """
    SELECT
        log_id,
        user_id,
        action_description,
        action_date
    FROM
        action_log
    ORDER BY
        action_date DESC;
    """

    with conn.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchall()

    return result

def register_user(conn, first_name, last_name, email, password):
    role_name = "client"
    with conn.cursor() as cursor:
        # Проверка, существует ли пользователь с таким email
        cursor.execute("SELECT user_id FROM users WHERE email = %s;", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            print(f"User with email {email} already exists.")
            return -1

        # Вызов хранимой функции для создания пользователя
        cursor.execute(
            "CALL create_user(%s, %s, %s, %s, %s);",
            (first_name, last_name, email, password, role_name)
        )


        # Получение user_id после создания пользователя
        cursor.execute(
            "SELECT user_id FROM users WHERE email = %s;",
            (email,)
        )
        result = cursor.fetchone()

        if result:
            user_id = result[0]
        else:
            user_id = -1
            
        conn.commit()
        
    return user_id



# Функция для входа в систему
def login(conn, email, password):
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT user_id FROM users WHERE email = %s AND password = %s;",
            (email, password)
        )
        result = cursor.fetchone()
        user_id = -1
        if result:
            user_id = result[0]
            print(f"You are logged in")
        else:
            print("Invalid email or password")
            
        conn.commit()
    return user_id
    
def get_user_role(conn, user_id):
    with conn.cursor() as cursor:
        cursor.execute("SELECT is_admin(%s);", (user_id,))
        result = cursor.fetchone()
        if result[0]:
            return 'admin'
        else:
            return 'client'
    
def change_first_name(conn, user_id, new_first_name):
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE users SET first_name = %s WHERE user_id = %s;",
            (new_first_name, user_id)
        )
        conn.commit()
        
        
def change_last_name(conn, user_id, new_second_name):
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE users SET last_name = %s WHERE user_id = %s;",
            (new_second_name, user_id)
        )
        conn.commit()
        
def change_password(conn, user_id, new_password):
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE users SET password = %s WHERE user_id = %s;",
            (new_password, user_id)
        )
        conn.commit()
        
def get_user_info(conn, user_id):
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT first_name, last_name, email FROM users WHERE user_id = %s;",
            (user_id,)
        )
        
        result = cursor.fetchone()
        print(f"Name: {result[0]}")
        print(f"Last name: {result[1]}")
        print(f"Email: {result[2]}")
        
        conn.commit()
        

def get_user_bookings(conn, user_id):
    result = -1
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT booking_id, room_id, arrival_date, departure_date, number_of_people FROM get_user_bookings(%s);",
            (user_id,)
        )
        result = cursor.fetchall()

    # Обработка результатов
        for i, row in enumerate(result, start=1):
            cursor.execute(
                "SELECT type_name FROM roomtypes WHERE room_type_id = (SELECT room_type_id FROM rooms WHERE room_id = %s);",
                (row[1],)
            )
            room_type_name = cursor.fetchone()[0]

            print(f"{i}. Room: {room_type_name}, Arrival date: {row[2]}, Departure date: {row[3]}, People number: {row[4]};")

    return result

def create_booking(conn, user_id, room_type_id, start_date, end_date, number_of_people):
    with conn.cursor() as cursor:
        try:
            cursor.execute(
                "CALL create_booking(%s, %s, %s, %s, %s);",
                (user_id, room_type_id, start_date, end_date, number_of_people)
            )
            conn.commit()
            print("Booking created successfully!")
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error creating booking: {e}")
            
def check_available_rooms(conn, start_date, end_date, room_type_id, number_of_people):
    with conn.cursor() as cursor:
        # Вызываем процедуру check_available_rooms
        cursor.execute(
            "SELECT * FROM check_available_rooms(%s, %s, %s);",
            (room_type_id, start_date, end_date)
        )

        # Получаем результат процедуры
        result = cursor.fetchone()
        
        cursor.execute(
            "SELECT max_people FROM roomtypes WHERE room_type_id = %s;",
            (room_type_id,)
        )
        
        result2 = cursor.fetchone()
        
        if result[0] != -1 & result2[0] >= number_of_people :
            return True
        else:
            return False
        
        
def add_service_to_booking(conn, booking_id):
    with conn.cursor() as cursor:
        try:
            # Get a list of all services not yet added to this booking
            cursor.execute(
                """
                SELECT s.service_name
                FROM services s
                WHERE s.service_id NOT IN (
                    SELECT sb.service_id
                    FROM servicesbookings sb
                    WHERE sb.booking_id = %s
                );
                """,
                (booking_id,)
            )
            available_services = cursor.fetchall()

            if not available_services:
                print("All services are already added to this booking.")
                return

            print("Available services for adding:")
            for i, service in enumerate(available_services, start=1):
                print(f"{i}. {service[0]}")

            # User selects the service number to add
            choice = input("Select the service number to add (or '0' to cancel): ")
            choice = int(choice)

            if choice == 0:
                print("Adding service canceled.")
                return

            selected_service = available_services[choice - 1][0]

            # Call the procedure to add the selected service to the booking
            cursor.execute(
                "CALL add_service_to_booking(%s, %s);",
                (booking_id, selected_service)
            )

            print(f"Service '{selected_service}' successfully added to booking.")

        except Exception as e:
            print(f"Error adding service to booking: {e}")
            
            
def remove_service_from_booking(conn, booking_id, booked_services):
    with conn.cursor() as cursor:
            if not booked_services:
                print("No services added to this booking.")
                return

            print("Services added to this booking:")
            for i, service in enumerate(booked_services, start=1):
                print(f"{i}. {service[0]}")

            # User selects the service number to delete
            choice = input("Select the service number to delete (or '0' to cancel): ")
            try:
                choice = int(choice)
            except Exception:
                print("Invalid choice. Deleting service canceled.")
                return

            if choice == 0:
                print("Deleting service canceled.")
                return
            elif choice > len(booked_services):
                print("Invalid choice. Deleting service canceled.")
                return
            
            selected_service = booked_services[choice - 1][1]

            # Call the procedure to delete the selected service from the booking
            cursor.execute(
                "CALL delete_service_for_booking_by_name(%s, %s);",
                (booking_id, selected_service)
            )

            print(f"Service '{selected_service}' successfully deleted from booking.")
    

def cancel_booking(conn, booking_id):
    with conn.cursor() as cursor:
        try:
            # Call the procedure to cancel the booking
            cursor.execute(
                "CALL delete_booking(%s);",
                (booking_id,)
            )

            print(f"Booking successfully canceled.")

        except Exception as e:
            print(f"Error canceling booking: {e}")  


def get_booking_info(conn, booking):
    with conn.cursor() as cursor:
        cursor.execute(
                "SELECT type_name FROM roomtypes WHERE room_type_id = (SELECT room_type_id FROM rooms WHERE room_id = %s);",
                (booking[1],)
            )
        room_type_name = cursor.fetchone()[0]

        print(f"Room: {room_type_name}")
        print(f"Arrival date: {booking[2]}")
        print(f"Departure date: {booking[3]}")
        print(f"People number: {booking[4]}")
        
        cursor.execute(
            "SELECT * FROM get_booking_services(%s);",
            (booking[0],)
        )

        result = cursor.fetchall()

        if not result:
            print(f"No services yet.")
        else:    
            print(f"Services: ")
            for i, service in enumerate(result, start=1):
                service_id, service_name, price = service
                print(f"{i}. {service_name}, Price: {price}$")
        
        while(True):
            print("Select function:")
            print("1. Add service")
            print("2. Remove service")
            print("3. Cancel booking")
            print("4. Back")
            choice = input("Enter your choice (1/2/3/4): ")
            if choice == "1":
                add_service_to_booking(conn,booking[0])
            elif choice == "2":
                remove_service_from_booking(conn, booking[0], result)
            elif choice == "3":
                cancel_booking(conn, booking[0])
                break
            elif choice == "4":
                break
            else:
                print("Invalid choice")
            

  
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

def get_user_auth(conn):
    user_id = -1
    while(user_id < 0):
        print("Select function:")
        print("1. Register User")
        print("2. Login")
        print("3. Exit")
        choice = input("Enter your choice (1/2/3): ")
        if choice == "1":
            first_name = input("Enter first name: ")
            last_name = input("Enter last name: ")
            email = input("Enter email: ")
            password = input("Enter password: ")
            user_id = register_user(conn, first_name, last_name, email, password)
        elif choice == "2":
            email = input("Enter email: ")
            password = input("Enter password: ")
            user_id = login(conn, email, password)
        elif choice == "3":
            break
        else:
            print("Invalid choice")
        
    return user_id

def get_user_choice_profile(conn, user_id):
    while(True):
        print("Select function:")
        print("1. Get my info")
        print("2. Change first name")
        print("3. Change last name")
        print("4. Change password")
        print("5. Back")
        choice = input("Enter your choice (1/2/3/4/5): ")
        if choice == "1":
            get_user_info(conn, user_id)
        elif choice == "2":
            new_first_name = input("Enter new first name: ")
            if len(new_first_name) < 50:
                change_first_name(conn, user_id, new_first_name)
            else:
                print("Length of the name must be < 50")
        elif choice == "3":
            new_last_name = input("Enter new last name: ")
            if len(new_last_name) < 50:
                change_last_name(conn, user_id, new_last_name)
            else:
                print("Length of the last name must be < 50")
        elif choice == "4":
            new_password = input("Enter new password: ")
            if len(new_password) < 100:
                change_password(conn, user_id, new_password)
            else:
                print("Length of the password must be < 100")
        elif choice == "5":
            return
        else:
            print("Invalid choice")
            
            
def get_user_choice_bookings(conn, user_id):
    while(True):
        print("Select function:")
        print("1. Get my bookings")
        print("2. Create new booking")
        print("3. Back")
        choice = input("Enter your choice (1/2/3): ")
        if choice == "1":
            while(True):
                bookings = get_user_bookings(conn, user_id)
                print("Select booking:")
                print("-1. Back")
                choice = input("Enter your choice(1/../-1): ")
                if choice == "-1":
                    break
                else:
                    try:
                        booking_number = int(choice)
                        if booking_number > len(bookings):
                            raise Exception("Invalid choice")
                        get_booking_info(conn, bookings[booking_number - 1])
                    except Exception:
                        print("Invalid choice")
        elif choice == "2":
            with conn.cursor() as cursor:
                start_date = input("Enter the start date (YYYY-MM-DD): ")
                end_date = input("Enter the end date (YYYY-MM-DD): ")

                if not is_valid_date(start_date) or not is_valid_date(end_date):
                    print("Error: Invalid date format. Please use YYYY-MM-DD.")
                    continue

                today = datetime.now().strftime("%Y-%m-%d")
                if start_date < today:
                    print("Error: Start date should be today or later.")
                    continue

                if end_date <= start_date:
                    print("Error: End date should be later than the start date.")
                    continue
                
                room_type_name = input("Enter the room type name(Single/Double/Suite): ")
                number_of_people = int(input("Enter the number of people: "))

                cursor.execute(
                    "SELECT room_type_id FROM roomtypes WHERE type_name = %s;",
                    (room_type_name,)
                )
                room_type_result = cursor.fetchone()

                if room_type_result:
                    room_type_id = room_type_result[0]
                    
                    if check_available_rooms(conn, start_date, end_date, room_type_id, number_of_people):
                        create_booking(conn, user_id, room_type_id, start_date, end_date, number_of_people)
                    else:
                        print(f"Error: Room type '{room_type_name}' is not available for the specified dates and number of people.")
                else:
                    print(f"Error: Room type '{room_type_name}' not found.")
        elif choice == "3":
            return
        else:
            print("Invalid choice")
            
def get_admin_choice_users(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM get_users_last_activity();")
        result = cursor.fetchall()
        for row in result:
            print(f"User ID: {row[0]}, Last Activity Date: {row[1]}")
        return result
    

def get_bookings_on_date(conn, date):
    if not is_valid_date(date):
        print("Invalid date format. Please use YYYY-MM-DD.")
        return

    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT user_id, booking_id, room_id, arrival_date, departure_date, number_of_people "
            "FROM get_bookings_on_date(%s);",
            (date,)
        )
        result = cursor.fetchall()

        if result:
            print("Bookings on", date)
            for row in result:
                print(f"User ID: {row[0]}, Booking ID: {row[1]}, Room ID: {row[2]}, "
                      f"Arrival Date: {row[3]}, Departure Date: {row[4]}, "
                      f"Number of People: {row[5]}")
        else:
            print("No bookings on", date)
            
def redistribute_rooms_by_type(conn, employee_type_id):
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM Rooms;")
        total_rooms = cursor.fetchone()[0]

            # Получаем количество сотрудников данного типа
        cursor.execute(
            "SELECT COUNT(*) FROM Employees WHERE employee_type_id = %s;", (employee_type_id,)
        )
        employees_count = cursor.fetchone()[0]

            # Вычисляем количество комнат на сотрудника и остаток
        if employees_count > 0:
            rooms_per_employee = total_rooms // employees_count
            remaining_rooms = total_rooms % employees_count
        else:
            rooms_per_employee = 0
            remaining_rooms = 0
        
        cursor.execute(
            "DELETE FROM RoomsEmployees WHERE employee_id IN (SELECT employee_id FROM Employees WHERE employee_type_id = %s);",
            (employee_type_id,),
        )
        
        
        query = """
                SELECT employee_id
                FROM employees
                WHERE employee_type_id = %s;
                """

        cursor.execute(query, (employee_type_id,))
        result = cursor.fetchall()
    
        employee_ids = [row[0] for row in result]
        
        
        query = """
                SELECT room_id
                FROM rooms;
                """

        cursor.execute(query)
        result = cursor.fetchall()

        room_ids = [row[0] for row in result]
        
        room_num = 0
        
        for employee_id in employee_ids:
            current_employee_rooms = rooms_per_employee
            if remaining_rooms > 0:
                current_employee_rooms += 1
                remaining_rooms -= 1
                
            while(current_employee_rooms > 0):
                cursor.execute("INSERT INTO roomsemployees (employee_id, room_id) VALUES (%s, %s);",
                               (employee_id, room_ids[room_num])
                               )
                room_num += 1
                current_employee_rooms -= 1
 
        
    conn.commit()         
            
def get_employee_type_id_by_name(conn, type_name):
    with conn.cursor() as cursor:
        cursor.execute("SELECT employee_type_id FROM employeetypes WHERE type_name = %s;", (type_name,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            raise ValueError(f"Employee type '{type_name}' not found.")
        

def create_employee(conn, name, phone, employee_type_name):
    # Получаем ID типа сотрудника по его имени
    try:
        employee_type_id = get_employee_type_id_by_name(conn, employee_type_name)
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO employees (name, phone, employee_type_id) VALUES (%s, %s, %s);",
                (name, phone, employee_type_id)
            )
            print(f"Employee {name} created")
        conn.commit()
    except ValueError:
        print("Incorrect employee type")
        return
    except:
        conn.rollback()
        print("Error")
        return
        
    redistribute_rooms_by_type(conn, employee_type_id)
    
def delete_employee(conn, employee_id):
    try:
        # Устанавливаем соединение с базой данных
        with conn.cursor() as cursor:
            # Получаем название типа сотрудника
            cursor.execute(
                "SELECT et.type_name "
                "FROM employees e "
                "JOIN employeetypes et ON e.employee_type_id = et.employee_type_id "
                "WHERE e.employee_id = %s;", (employee_id,)
            )
            employee_type_name = cursor.fetchone()[0]
            employee_type_id = get_employee_type_id_by_name(conn, employee_type_name)

            cursor.execute("DELETE FROM employees WHERE employee_id = %s;", (employee_id,))

            cursor.execute("DELETE FROM roomsemployees WHERE employee_id = %s;", (employee_id,))
            print("Employee deleted succesfully")
            conn.commit()
    except:
        # Обработка ошибок
        print("Incorrect employee id")
        conn.rollback()
        return
    redistribute_rooms_by_type(conn, employee_type_id)


def get_employees_by_type_and_room(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM get_employees_by_type_and_room();")
        result = cursor.fetchall()

        if result:
            print("Employees:")
            for row in result:
                print(f"Employee ID: {row[0]}, Name: {row[1]}, Phone: {row[2]}, Type: {row[3]}, Room Number: {row[4]}")
        else:
            print("No employees found.")
            
        while(True):
            choice = input("Would you like to add or delete employee? 1 - add, 2 - delete, 3 - back: ")
            if choice == "1":
                name = input("Enter name: ")
                phone = input("Enter phone: ")
                employee_type_name = input("Enter employee type: ")
                create_employee(conn, name, phone, employee_type_name)
                break
            elif choice == "2":
                try:
                    employee_id = int(input("Enter employee id: "))
                except:
                    print("Incorrect id")
                    continue
                delete_employee(conn, employee_id)
                break
            elif choice == "3":
                return
            else:
                print("Incorrect choice")
            
            
def create_review(conn, mark, text, user_id):
    try:
        int_mark = int(mark)
        with conn.cursor() as cursor:
            cursor.execute(
                "CALL create_review(%s, %s, %s);",
                (int_mark, text, user_id)
            )
            conn.commit()
            print("Review created succesfully.")
    except:
        conn.rollback()
        print(f"Error. Mark should be between 1 and 5.")
        
def update_review(conn, user_id, new_mark, new_text):
    try:
        int_new_mark = int(new_mark)
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT review_id
                FROM reviews
                WHERE user_id = %s
                LIMIT 1;
                """,
                (user_id,)
            )
            review_id = cursor.fetchone()

            review_id = review_id[0]

                # Обновляем отзыв
            cursor.execute(
                """
                UPDATE reviews
                SET mark = %s, text = %s
                WHERE review_id = %s;
                """,
                (int_new_mark, new_text, review_id)
            )
    
            conn.commit()
    except:
        conn.rollback()
        print(f"Error. Mark should be between 1 and 5.")
        
        
def delete_review(conn, user_id):
    try:
        with conn.cursor() as cursor:
            # Выбираем первый отзыв пользователя по user_id
            cursor.execute(
                """
                SELECT review_id
                FROM reviews
                WHERE user_id = %s
                LIMIT 1;
                """,
                (user_id,)
            )
            review_id = cursor.fetchone()

            review_id = review_id[0]

            cursor.execute(
                """
                DELETE FROM reviews
                WHERE review_id = %s;
                """,
                (review_id,)
            )

            conn.commit()
            print("Review deleted succesfully")
    except:
        conn.rollback()
        print("Error")

def get_user_choice_review(conn, user_id):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT * FROM get_user_review(%s);
            """,
            (user_id,)
        )

        result = cursor.fetchall()
        if not result:
            while(True):
                choice = input("You have no review yet. Would you like to create it?(1 - yes, 2 - no):")
                if choice == "1":
                    mark = input("Enter mark: ")
                    text = input("Enter comment: ")
                    create_review(conn, mark, text, user_id)
                    return
                elif choice == "2":
                    return
                else:
                    print("Incorrect choice")
                
        else:
            while(True):
                for row in result:
                    print(f"Rating: {row[2]}, Comment: {row[3]}")
                    
                choice = input("Would you like to delete or modify your review(1- delete, 2 - change, 3 - back)")
                
                if choice == "1":
                    delete_review(conn, user_id)
                    return
                if choice == "2":
                    mark = input("Enter mark: ")
                    text = input("Enter comment: ")
                    update_review(conn, user_id, mark, text)
                    return
                elif choice == "3":
                    return
                else:
                    print("Incorrect choice")

            

def get_user_choice_menu(conn, p_user_id):
    user_id = p_user_id
    while(True):
        print("Select function:")
        print("1. Profile")
        print("2. Bookings")
        print("3. Review")
        print("4. Exit")
        choice = input("Enter your choice (1/2/3/4): ")
        if choice == "1":
            get_user_choice_profile(conn, user_id)
        elif choice == "2":
            get_user_choice_bookings(conn, user_id)
        elif choice == "3":
            get_user_choice_review(conn, user_id)
        elif choice == "4":
            return
        else:
            print("Invalid choice")
            
def get_admin_choice_menu(conn, p_user_id):
    user_id = p_user_id
    while(True):
        print("Select function:")
        print("1. Users")
        print("2. Bookings")
        print("3. Employees")
        print("4. Exit")
        choice = input("Enter your choice (1/2/3/4): ")
        if choice == "1":
            while(True):
                get_admin_choice_users(conn)
                print("Select function:")
                print("1. Delete")
                print("2. Make admin")
                print("3. Back")
                choice2 = input("Enter your choice (1/2/3): ")
                if choice2 == "1":
                    with conn.cursor() as cursor:
                        try:
                            choice3 = int(input("Enter user id: "))
                            cursor.execute(
                                "CALL delete_user(%s);",
                                (choice3, )
                                )
                            conn.commit()
                            print("User deleted successfully!")
                        except:
                            print("Incorrect choice")
                if choice2 == "2":
                    with conn.cursor() as cursor:
                        try:
                            choice3 = int(input("Enter user id: "))
                            cursor.execute(
                                "CALL change_user_role_to_admin(%s);",
                                (choice3, )
                                )
                            conn.commit()
                            print(f"User with id: {choice3} is admin!")
                        except:
                            print("Incorrect choice")
                if choice2 == "3":
                    break
                else:
                    print("Incorrect choice")
        elif choice == "2":
            choice2 = input("Enter date: ")
            get_bookings_on_date(conn, choice2)
        elif choice == "3":
            get_employees_by_type_and_room(conn)
        elif choice == "4":
            return
        else:
            print("Invalid choice")
    
            

conn = psycopg2.connect(host='localhost', user='postgres', password='1234567', dbname='hotel_db')
user_role = ''
user_id = get_user_auth(conn)
if user_id > 0:
    user_role = get_user_role(conn, user_id)
    if user_role == "admin":
        get_admin_choice_menu(conn, user_id)
    elif user_role == "client":
        get_user_choice_menu(conn, user_id)


conn.close()
