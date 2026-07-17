# pip install reportlab
# One-off generator for synthetic, clearly-fictional company policy PDFs used
# by this demo. Run this once (or whenever you want to regenerate data/) before
# running policy_rag_agent.py.
import os
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

POLICIES = {
    "HR Policy.pdf": (
        "HR Policy",
        [
            ("Working Hours and Attendance",
             "Standard working hours at Acme Corp are 9:00 AM to 6:00 PM, Monday through Friday, "
             "with a one-hour lunch break. Employees are expected to log attendance through the "
             "company HR portal daily. Persistent unexplained absence may result in disciplinary action."),
            ("Probation Period",
             "All new employees serve a probation period of 6 months from their date of joining. "
             "Confirmation of employment is subject to a satisfactory performance review conducted "
             "by the employee's manager at the end of this period."),
            ("Performance Reviews",
             "Formal performance reviews are conducted twice a year, in April and October. Ratings "
             "from these reviews feed into annual compensation revisions and promotion decisions."),
            ("Exit Process and Full & Final Settlement",
             "Employees who resign must serve the notice period specified in their offer letter "
             "(typically 30 to 90 days depending on grade). Full and final settlement, including any "
             "payable leave encashment as described in the Leave Policy, is processed within 45 days "
             "of the last working day, subject to completion of the exit checklist and return of "
             "company assets as described in the Laptop Policy."),
            ("Grievance Redressal",
             "Employees with workplace grievances should first raise the matter with their reporting "
             "manager. If unresolved, grievances may be escalated to HR Business Partners, and "
             "further to the Ethics Committee for matters covered under the Code of Conduct."),
        ],
    ),
    "Leave Policy.pdf": (
        "Leave Policy",
        [
            ("Types of Leave",
             "Employees are entitled to 18 days of annual leave, 10 days of casual/sick leave, and "
             "public holidays as declared by the company each calendar year."),
            ("Applying for Leave",
             "Leave requests must be submitted through the HR portal at least 3 working days in "
             "advance, except for sick leave, which may be applied for on the day of absence."),
            ("Carry Forward of Annual Leave",
             "Employees who remain with the company may carry forward a maximum of 10 unused annual "
             "leave days into the next calendar year. Any balance beyond 10 days will lapse."),
            ("Leave Encashment on Resignation",
             "Employees who resign are NOT eligible to carry forward unused annual leave to a future "
             "period. Instead, any unused annual leave balance at the time of resignation, up to a "
             "maximum of 15 days, will be encashed and paid out as part of the full and final "
             "settlement described in the HR Policy. Leave balances beyond 15 days are forfeited "
             "and are not paid out."),
            ("Sick Leave Rules",
             "Sick leave exceeding 3 consecutive days requires a medical certificate to be uploaded "
             "to the HR portal. Unused sick leave cannot be carried forward or encashed under any "
             "circumstances."),
        ],
    ),
    "Travel Policy.pdf": (
        "Travel Policy",
        [
            ("Booking Business Travel",
             "All domestic and international business travel must be booked through the approved "
             "corporate travel desk. Economy class is standard for domestic travel; Premium Economy "
             "is permitted for international flights exceeding 6 hours."),
            ("Hotel Accommodation",
             "Employees should book 3-star or 4-star hotel accommodation within the per-city rate "
             "caps published on the HR portal. Any exception requires manager pre-approval."),
            ("Local Conveyance and Taxi Expenses",
             "Local conveyance incurred during official business travel, including taxis, ride-hailing "
             "services such as Uber or Ola, and airport transfers, are reimbursable expenses. Employees "
             "must retain receipts for any single taxi fare exceeding USD 10. Where a receipt is "
             "unavailable, a self-certified expense entry may be used for smaller amounts, subject to "
             "manager approval. All such claims should be filed following the standard reimbursement "
             "process described in the Expense Policy, within 30 days of completing travel."),
            ("Travel Advances",
             "Employees travelling internationally may request a travel advance of up to USD 500 "
             "through the Expense Policy's advance request workflow, to be settled within 15 days "
             "of return."),
            ("Per Diem",
             "A daily meal per diem applies for outstation travel, at rates published on the HR "
             "portal by destination city, and does not require itemized receipts."),
        ],
    ),
    "Expense Policy.pdf": (
        "Expense Policy",
        [
            ("Filing an Expense Claim",
             "All business expense claims must be filed through the Expense Management System within "
             "30 days of the expense being incurred. Claims filed after 60 days will not be reimbursed "
             "without VP-level approval."),
            ("Receipt Requirements",
             "Original itemized receipts are required for all expenses above USD 25. For smaller "
             "expenses, such as local taxi fares described in the Travel Policy, a self-certified "
             "entry is acceptable."),
            ("Approval Workflow",
             "Expense claims are routed to the employee's direct manager for approval, followed by "
             "Finance review for amounts exceeding USD 1,000."),
            ("Reimbursement Timeline",
             "Approved claims are reimbursed with the next payroll cycle, typically within 15 "
             "business days of final approval."),
            ("Non-Reimbursable Items",
             "Personal entertainment, traffic and parking fines, alcohol (outside of approved client "
             "entertainment budgets), and airline seat upgrades are not reimbursable."),
        ],
    ),
    "IT Security.pdf": (
        "IT Security Policy",
        [
            ("Password and Authentication",
             "All company accounts require multi-factor authentication (MFA). Passwords must be at "
             "least 12 characters and rotated every 90 days."),
            ("Device Encryption",
             "All company-issued laptops, as covered under the Laptop Policy, must have full-disk "
             "encryption enabled before being used to access company systems."),
            ("Data Classification",
             "Company data is classified as Public, Internal, Confidential, or Restricted. Confidential "
             "and Restricted data must never be stored on personal devices or personal cloud storage."),
            ("Incident Reporting",
             "Any suspected security incident, including phishing emails, lost devices, or unauthorized "
             "access, must be reported to security@acmecorp.example within 1 hour of discovery."),
            ("Acceptable Use",
             "Installation of unapproved third-party software on company devices is prohibited without "
             "prior IT approval."),
        ],
    ),
    "Code of Conduct.pdf": (
        "Code of Conduct",
        [
            ("Ethical Standards",
             "All employees are expected to act with honesty and integrity in all business dealings, "
             "and to avoid conflicts of interest between personal and company interests."),
            ("Anti-Harassment",
             "Acme Corp maintains a zero-tolerance policy toward harassment or discrimination of any "
             "kind. Violations should be reported to HR or the Ethics Committee as described in the "
             "HR Policy's grievance redressal process."),
            ("Gifts and Entertainment",
             "Employees may not accept gifts from vendors or clients valued above USD 50 without "
             "disclosure to their manager and Compliance."),
            ("Confidentiality",
             "Employees must not disclose confidential company information, as classified under the "
             "IT Security Policy, to any external party without authorization."),
            ("Reporting Violations",
             "Violations of this Code of Conduct can be reported confidentially through the Ethics "
             "Hotline, and will be investigated by the Ethics Committee."),
        ],
    ),
    "Remote Work.pdf": (
        "Remote Work Policy",
        [
            ("Eligibility",
             "Employees in roles designated as hybrid-eligible by their department head may work "
             "remotely up to 3 days per week."),
            ("Equipment",
             "Remote employees are issued a company laptop and monitor per the Laptop Policy. Home "
             "internet costs are not reimbursed unless specified in the employee's offer letter."),
            ("Working Hours",
             "Remote employees are expected to be available during core hours of 10:00 AM to 4:00 PM "
             "local time, consistent with the working hours defined in the HR Policy."),
            ("Security Requirements",
             "Remote work requires use of the company VPN and adherence to the device encryption and "
             "data classification rules in the IT Security Policy."),
            ("Communication Norms",
             "Remote employees should keep their calendar status updated and respond to messages "
             "within 4 business hours during core working hours."),
        ],
    ),
    "Benefits.pdf": (
        "Employee Benefits",
        [
            ("Health Insurance",
             "All full-time employees are enrolled in the company group health insurance plan from "
             "their date of joining, with details described in the Medical Insurance policy."),
            ("Retirement Savings",
             "The company contributes 6% of base salary to the employee's retirement savings account, "
             "matching employee contributions up to an additional 4%."),
            ("Wellness Program",
             "Employees have access to an annual wellness allowance of USD 300 for gym memberships, "
             "fitness classes, or mental health services."),
            ("Employee Assistance Program",
             "A confidential Employee Assistance Program (EAP) offers counseling and support services "
             "to employees and their immediate family members at no cost."),
            ("Other Perks",
             "Additional perks include an annual learning and development stipend of USD 500 and "
             "discounted meals at office cafeterias."),
        ],
    ),
    "Laptop Policy.pdf": (
        "Laptop Policy",
        [
            ("Issuance",
             "All employees are issued a standard-configuration company laptop upon joining, selected "
             "based on role requirements as approved by IT."),
            ("Acceptable Use",
             "Company laptops must only be used for business purposes and must comply with the "
             "acceptable use and encryption rules in the IT Security Policy."),
            ("Damage and Loss",
             "Accidental damage is covered once per year at no cost to the employee. Repeated damage "
             "or loss due to negligence may result in a deduction from the employee's final settlement "
             "as described in the HR Policy."),
            ("Return on Exit",
             "All company equipment, including laptops, monitors, and access cards, must be returned "
             "on or before the last working day. Full and final settlement, per the HR Policy, is "
             "contingent on equipment return."),
            ("BYOD",
             "Personal devices are not permitted to access confidential or restricted company data as "
             "classified under the IT Security Policy."),
        ],
    ),
    "Medical Insurance.pdf": (
        "Medical Insurance Policy",
        [
            ("Coverage",
             "The company-sponsored medical insurance plan covers hospitalization, day-care procedures, "
             "and pre/post-hospitalization expenses up to USD 20,000 per policy year."),
            ("Family Coverage",
             "Employees may add their spouse and up to two children to the group medical insurance "
             "plan during the annual enrollment window or within 30 days of a qualifying life event."),
            ("Claim Process",
             "Cashless claims can be filed directly at any network hospital. Reimbursement claims for "
             "non-network hospitals must be submitted within 30 days of discharge, along with original "
             "bills and discharge summary."),
            ("Network Hospitals",
             "A list of network hospitals offering cashless treatment is published on the HR portal "
             "and updated quarterly."),
            ("Pre-Existing Conditions",
             "Pre-existing conditions are covered from the first day of enrollment, with no waiting "
             "period, for all employees who enroll during their initial eligibility window."),
        ],
    ),
}

def generate_policy_pdf(filename: str, title: str, sections: list[tuple[str, str]]):
    styles = getSampleStyleSheet()
    path = os.path.join(DATA_DIR, filename)
    doc = SimpleDocTemplate(path, pagesize=LETTER)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 16)]

    for heading, body in sections:
        story.append(Paragraph(heading, styles["Heading2"]))
        story.append(Spacer(1, 6))
        story.append(Paragraph(body, styles["BodyText"]))
        story.append(Spacer(1, 14))

    doc.build(story)
    print(f"Generated {path}")

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    for filename, (title, sections) in POLICIES.items():
        generate_policy_pdf(filename, title, sections)
