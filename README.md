# Pojangmacha

## Project Overview & Problem Statement  
Pojangmacha is a food-ordering and management system developed using **Python** and **Flet**. It provides a user-friendly interface for customers to browse menu items, place orders, and track their status in real time. Administrators can manage menu items, process customer orders, and view basic business analytics.  

The project addresses the challenges of manual order tracking, slow inventory updates, and lack of actionable data, offering a streamlined desktop/mobile-inspired GUI application suitable for small eateries.  

## Feature List & Scope  
| Feature / Module | In Scope (✓) / Out of Scope (✗) | Notes / Limitations |
|------------------|-------------------------------|---------------------|
| Customer Order UI | ✓ | Browse menu, select quantity, place orders, track status |
| Admin Dashboard | ✓ | Add/edit/delete menu items, manage orders, view summary stats |
| Data Visualization | ✓ | Interactive charts showing live or processed data |
| Payment Integration | ✗ | Not implemented yet |
| Inventory Forecasting | ✗ | Planned for future releases |

## Architecture Diagram  
```
[ Flet UI layer ]  ↔  [ Core logic / controllers ]  ↔  [ SQLite database ]
                     ↕
        [ Emerging Tech: Interactive Data Visualization ]
```
**Folder Structure:**  
- `/core` – shared logic and utilities  
- `/models` – data models and database handlers  
- `/ui` – customer and admin interface screens  
- `/assets` – images and icons  
- `main.py` – application entry point
- `init_db.py` - setup and migration scripts 

## Data Model  
Example JSON schema:  

**User**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "password_hash": "hashed_pw",
  "role": "customer"
}
```

**FoodItem**
```json
{
  "id": 101,
  "name": "BimBimBowl",
  "description": "Rice, Egg, Carrot, ...",
  "category": "Korean Bowls",
  "price": 100.0,
  "image": "assets/uploads/foods/bimbimbowl.jpg"
}
```

**Order**
```json
{
  "id": 2001,
  "user_id": 1,
  "status": "pending",
  "created_at": "2024-06-01T12:00:00"
}
```

**OrderItem**
```json
{
  "id": 3001,
  "order_id": 2001,
  "food_item_id": 101,
  "quantity": 2,
  "price": 200.0
}
```

**Cart**
```json
{
  "id": 4001,
  "user_id": 1
}
```

**AuditLog**
```json
{
  "id": 5001,
  "user_id": 1,
  "action": "login",
  "timestamp": "2024-06-01T12:00:00"
}
```

**LoginAttempt**
```json
{
  "id": 6001,
  "email": "user@example.com",
  "success": false,
  "attempt_time": "2024-06-01T12:00:00",
  "locked_until": null,
  "failed_attempts": 3
}
```

All persistent data (menu items, orders) are stored in a centralized **SQLite database**, initialized via `init_db.py`.

## Emerging Tech Explanation  
We integrate **interactive data visualization** to provide admins with actionable insights. Unlike static charts, these visualizations reflect live or processed user data:  
- Real-time monitoring of orders and sales  
- Quick identification of trends and anomalies  
- Enhanced decision-making based on interactive charts  

**Why chosen:** Improves usability and allows the system to communicate complex data simply.  

**Integration:** Embedded directly in the Flet interface, connected to backend data for dynamic updates.  

**Limitations:**  
- Performance may degrade with very large datasets  
- Real-time updates depend on refresh frequency  
- Supports basic charts (bar, line, pie); advanced analytics planned  

## Setup & Run Instructions  
1. Clone the repository:  
```bash
git clone https://github.com/Dev-Gab02/Pojangmacha.git
cd Pojangmacha
```  
2. Create and activate a virtual environment:  
```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```  
3. Install dependencies:  
```bash
pip install -r requirements.txt
```  
4. Initialize the database:  
```bash
python init_db.py
```  
5. Google OAuth Setup:
```bash
- Obtain your credentials.json from the Google Cloud Console.
- Place the credentials.json file in the project root directory (Pojangmacha/).
- (Optional) If your app generates a token.json after the first Google login, it will be saved in the same directory.
- Do not commit these files to version control.
```  
6. Run the application:  
```bash
python main.py
```  
**Supported Platforms:** Windows, Linux (Python 3.13 recommended)  

## Testing Summary  
**How to Run Tests:**
- Manual testing is performed by running the app and verifying all user and admin flows.
- To test, launch the app with:
```bash
python main.py
```  
- Log in as both user and admin.

**To login as admin:**
```bash
Email: admin@gmail.com
Password: admin123
```  
- lace orders, reset passwords, and test lockout scenarios.
- Check all navigation routes, authentication, menu management, cart, order history, and analytics dashboard.
- Confirm window resizing and UI responsiveness on both desktop and mobile layouts.  

## Team Roles & Contribution Matrix  
| Contributor | Role / Responsibilities | Contributions / Modules |
|-------------|------------------------|------------------------|
| Gabriel Concepcion (Dev-Gab02) | Backend logic / Core logic / Project lead/ Data model | Flet UI, main app flow, SQLite schema, init_db scripts |
| John Patrick Panoy (johnpatrick1518)| UI / Documentation | Flet UI, Documentation & README |
| John Wilbert Carullo (johncarullo-netizen)| Testing | Test scripts|

## Risk / Constraints & Future Enhancements  
**Risks / Constraints:**  
- No payment gateway yet  
- Local data only; no cloud sync  
- Large datasets may impact live chart performance  

**Future Enhancements:**  
- Add payment integration and multi-restaurant support  
- Expand analytics dashboard with predictive insights  
- Packaged desktop or mobile application deployment  

## Individual Reflection  

**Gabriel Concepcion (Dev-Gab02):**  
As the backend and core logic lead, I focused on designing the data model, implementing the SQLite schema, and developing the main application flow. Integrating the backend with the Flet UI while maintaining data integrity was a major challenge, especially ensuring real-time order updates and seamless interaction between user and admin interfaces. Through this project, I enhanced my skills in full-stack development, database design, and coordinating multiple components in a modular and maintainable way. Leading the project also taught me valuable lessons in time management, planning tasks, and collaborating closely with teammates. Overall, I gained a deeper understanding of how to connect backend logic with interactive front-end elements and ensure a robust, scalable system. 

**John Patrick Panoy:**  
My primary role was UI development and documentation. I worked on designing user-friendly screens in Flet, ensuring the interface was intuitive for both customers and admins. Creating clear and comprehensive documentation, including the README and supporting materials, helped consolidate the team’s work into a reference that others can understand and follow. I learned how important UI consistency and clarity are in enhancing user experience, as well as how documentation strengthens team communication and project maintainability. This project improved my skills in front-end design, technical writing, and bridging design with functional implementation.  

**John Wilbert Carullo:**  
I was responsible for testing and quality assurance. My focus was on developing test scripts to validate the correctness of order processing, data persistence, and integration between UI and backend. Testing the real-time updates and live visualizations required careful planning and simulation to ensure reliability. This experience strengthened my skills in debugging, structured testing, and identifying edge cases in a dynamic application. I also gained insight into how testing interacts with both backend logic and UI components, reinforcing the importance of thorough validation in a full-stack system. Overall, contributing to Pojangmacha helped me understand quality assurance in a practical, project-driven environment. 

---

## Acknowledgments  
- Acknowledgments: Flet framework, SQLite, and open-source inspirations  


## APP
![alt text](<assets/uploads/app/Screenshot 2025-12-09 022542.png>)
![alt text](<assets/uploads/app/Screenshot 2025-12-09 022626.png>)
![alt text](<assets/uploads/app/Screenshot 2025-12-09 022725.png>)
![alt text](<assets/uploads/app/Screenshot 2025-12-09 022757.png>)
![alt text](<assets/uploads/app/Screenshot 2025-12-09 022821.png>)
![alt text](<assets/uploads/app/Screenshot 2025-12-09 022909.png>)
![alt text](<assets/uploads/app/Screenshot 2025-12-09 022934.png>)
![alt text](<assets/uploads/app/Screenshot 2025-12-09 023534.png>)
![alt text](<assets/uploads/app/Screenshot 2025-12-09 023606.png>)