REASON_TEMPLATES = {
    "📞 Contact / Transfer Issues": [
        {"label": "Call dropped / No answer", "template": "Call dropped. I tried to call back without answer. Please call the Cx back.", "inputs": []},
        {"label": "Transfer failed / No answer", "template": "Cx wasn't transferred to me. I tried to call back, without answer.", "inputs": []},
        {"label": "Cx requested Sales Agent", "template": "At the end of the call, the Cx expressed concern about proceeding with the enrollment process and requested to speak with the sales agent again before moving forward.", "inputs": []},
    ],
    "🆔 Identity Verification (PII)": [
        {"label": "DOB Incorrect", "template": "The DOB is incorrect, the correct one is: {}", "inputs": ["Correct DOB"]},
        {"label": "SSN Incorrect", "template": "The SSN is incorrect, the correct one is: {}", "inputs": ["Correct SSN"]},
        {"label": "Unable to verify SSN", "template": "The Cx was unable to verify the SSN.", "inputs": []},
        {"label": "Declined Personal Info", "template": "The Customer declined to provide personal information for verification.", "inputs": []},
    ],
    "🏦 Banking Information": [
        {"label": "Bank Name Incorrect", "template": "The bank name listed for the client’s account is incorrect. The correct name should be: {}", "inputs": ["Correct Bank Name"]},
        {"label": "Account # Incorrect", "template": "The account number is incorrect. The correct number is: {}", "inputs": ["Correct Account #"]},
        {"label": "Routing # Incorrect", "template": "The routing number is incorrect. The correct number is: {}", "inputs": ["Correct Routing #"]},
        {"label": "Unable to verify Bank Info", "template": "The Cx was unable to verify the account number and routing number.", "inputs": []},
        {"label": "Refused Banking Info", "template": "The Cx refused to provide their banking info.", "inputs": []},
        {"label": "FULL Banking Correction", "template": "According to the Cx, the banking info should be:\n      Bank: {}\n      Account #: {}\n      Routing #: {}", "inputs": ["Bank Name", "Account #", "Routing #"]},
    ],
    "📅 Program Details": [
        {"label": "Payment Amount Incorrect", "template": "According to the Cx, their payments should be {}, instead of {}.", "inputs": ["Correct Amount", "Wrong Amount"]},
        {"label": "1st Payment Date Incorrect", "template": "According to the Cx, the first payment date is incorrect. The correct date should be: {}", "inputs": ["Correct Date"]},
        {"label": "Program Length Incorrect", "template": "According to the Cx, the program length should be {} months, instead of {} months.", "inputs": ["Correct Months", "Wrong Months"]},
        {"label": "Insufficient Income", "template": "The Cx stated that he/she does not have sufficient income to afford the program.", "inputs": []},
    ],
    "🚫 Objections / Legal": [
        {"label": "Active Military", "template": "The Cx stated that he/she is active military, making him/her ineligible for the program.", "inputs": []},
        {"label": "Does not recognize debt", "template": "The Cx does not recognize this debt and requires clarification before enrolling in the program: {}", "inputs": ["Which debt?"]},
        {"label": "Wants to ADD debt", "template": "Cx wants to add another debt.", "inputs": []},
        {"label": "Remove specific debt", "template": "Cx doesn't want to include this debt in the program: {}", "inputs": ["Which debt?"]},
        {"label": "Right of Offset Concern", "template": "The Cx is concerned that the right of offset may apply.", "inputs": []},
        {"label": "Immediate Payments Misconception", "template": "The Cx believed we would begin making payments to the creditors immediately. We clarified that, under the program, payments are only made once an agreement has been reached with the creditors. However, the Cx disagreed.", "inputs": []},
        {"label": "Credit Score Concern", "template": "The Cx is concerned about their credit score being negatively affected. We explained that credit may be impacted during the program, but the Cx disagreed.", "inputs": []},
        {"label": "Government Program Misconception", "template": "The Cx believed we were a government program. We clarified that we are a private legal firm, not a government program. However, the Cx chose not to continue with us.", "inputs": []},
        {"label": "Lawsuit/Sued Concern", "template": "The Cx expressed concern about the possibility of being sued by their creditors. We explained that, if this occurs, they will have our legal representation. However, the Cx was not comfortable with this.", "inputs": []},
        {"label": "Loan Misconception", "template": "The Cx thought that we were going to loan him money so that the Cx won't have to pay their creditors no more and pay to us instead.", "inputs": []},
        {"label": "Consolidation Misconception", "template": "The Cx believed we were a consolidation program. We clarified that we are a settlement program, where the Cx makes payments to us and we use those funds to settle their debts. However, the Cx chose not to continue with us.", "inputs": []},
    ]
}