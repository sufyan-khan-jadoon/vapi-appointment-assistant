# Step1: Import Database objects

from database import init_db, Appointment, get_db


init_db()

# Step3: Create Data Contracts using Pydantic Models
import datetime as dt
import difflib
from pydantic import BaseModel


def normalize_name(name: str) -> str:
    return " ".join(name.strip().split()).title()


def normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    return digits if digits else phone.strip()


class AppointmentRequest(BaseModel):
    patient_name: str
    patient_phone: str | None = None
    purpose: str
    patient_age: str | None = None
    patient_gender: str | None = None
    date: str

class AppointmentResponse(BaseModel):
    id: int
    patient_name: str
    patient_phone: str | None
    purpose: str
    patient_age: str | None
    patient_gender: str | None
    date: str
    token_number: int
    canceled: bool
    created_at: dt.datetime

class CancelAppointmentRequest(BaseModel):
    patient_name: str | None = None
    patient_phone: str | None = None
    date: dt.date

class CancelAppointmentResponse(BaseModel):
    canceled_count: int

# Step2: Create FastAPI application and endpoints pseudo code

from fastapi import FastAPI, HTTPException, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import select, func


app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "success", "message": "Sunrise Family Clinic Appointment Assistant is live!"}

# Vapi Webhook Models
class VapiToolCall(BaseModel):
    id: str
    tool: dict
    function: dict

class VapiMessage(BaseModel):
    message: dict

@app.post("/vapi-webhook/")
async def vapi_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Bridge between Vapi tool calls and our backend functions.
    """
    data = await request.json()
    
    # Check if this is a tool-call message
    message = data.get("message", {})
    if message.get("type") != "tool-call":
        return {"status": "ignored", "type": message.get("type")}
    
    tool_calls = message.get("toolCallList", [])
    results = []
    
    for call in tool_calls:
        tool_id = call.get("id")
        function = call.get("function", {})
        name = function.get("name")
        args = function.get("arguments", {})
        
        try:
            if name == "parse_date":
                # Convert date_string to DateParseRequest
                parse_req = DateParseRequest(date_string=args.get("date_string"))
                res = parse_date(parse_req)
                results.append({"toolCallId": tool_id, "result": res.dict()})
                
            elif name == "schedule_appointment":
                # Convert args to AppointmentRequest
                # Vapi might send date as 'date' or 'date_string'
                appt_req = AppointmentRequest(
                    patient_name=args.get("patient_name"),
                    patient_phone=args.get("patient_phone"),
                    purpose=args.get("purpose"),
                    patient_age=str(args.get("patient_age")) if args.get("patient_age") else None,
                    patient_gender=args.get("patient_gender"),
                    date=args.get("date")
                )
                res = schedule_appointment(appt_req, db)
                results.append({"toolCallId": tool_id, "result": res.dict()})
                
            elif name == "cancel_appointment":
                # Convert args to CancelAppointmentRequest
                cancel_req = CancelAppointmentRequest(
                    patient_name=args.get("patient_name"),
                    patient_phone=args.get("patient_phone"),
                    date=dt.date.fromisoformat(args.get("date"))
                )
                res = cancel_appointment(cancel_req, db)
                results.append({"toolCallId": tool_id, "result": res.dict()})
                
            elif name == "list_appointments":
                date_val = dt.date.fromisoformat(args.get("date"))
                res = list_appointments(date_val, db)
                results.append({"toolCallId": tool_id, "result": [r.dict() for r in res]})
            
            else:
                results.append({"toolCallId": tool_id, "error": f"Unknown tool: {name}"})
                
        except Exception as e:
            results.append({"toolCallId": tool_id, "error": str(e)})
            
    return {"results": results}

# Helper endpoint for parsing relative dates
class DateParseRequest(BaseModel):
    date_string: str

class DateParseResponse(BaseModel):
    date: str
    day_name: str

@app.post("/parse_date/")
def parse_date(request: DateParseRequest):
    """
    Parse relative date strings like 'Thursday', 'next week', 'upcoming Thursday' to YYYY-MM-DD format
    """
    date_str = request.date_string.lower().strip()
    today = dt.date.today()
    
    # Map day names to weekday numbers (0=Monday, 6=Sunday)
    days = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    try:
        # Check if it's a weekday name like Thursday
        for day_name, day_num in days.items():
            if day_name in date_str:
                current_weekday = today.weekday()
                days_ahead = day_num - current_weekday
                if days_ahead <= 0:
                    days_ahead += 7
                next_date = today + dt.timedelta(days=days_ahead)
                return DateParseResponse(
                    date=next_date.isoformat(),
                    day_name=day_name.capitalize()
                )

        # Try direct YYYY-MM-DD format
        try:
            parsed_date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
            return DateParseResponse(
                date=parsed_date.isoformat(),
                day_name=parsed_date.strftime("%A")
            )
        except ValueError:
            pass

        # Try to parse month/day phrases like April 15 or April fifteenth
        month_names = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }

        # Normalize ordinal words to numbers
        ordinals = {
            'first': 1, 'second': 2, 'third': 3, 'fourth': 4,
            'fifth': 5, 'sixth': 6, 'seventh': 7, 'eighth': 8,
            'ninth': 9, 'tenth': 10, 'eleventh': 11, 'twelfth': 12,
            'thirteenth': 13, 'fourteenth': 14, 'fifteenth': 15,
            'sixteenth': 16, 'seventeenth': 17, 'eighteenth': 18,
            'nineteenth': 19, 'twentieth': 20, 'twenty first': 21,
            'twenty-first': 21, 'twenty second': 22, 'twenty-second': 22,
            'twenty third': 23, 'twenty-third': 23, 'twenty fourth': 24,
            'twenty-fourth': 24, 'twenty fifth': 25, 'twenty-fifth': 25,
            'twenty sixth': 26, 'twenty-sixth': 26, 'twenty seventh': 27,
            'twenty-seventh': 27, 'twenty eighth': 28, 'twenty-eighth': 28,
            'twenty ninth': 29, 'twenty-ninth': 29, 'thirtieth': 30,
            'thirty first': 31, 'thirty-first': 31
        }

        normalized = date_str.replace('-', ' ').replace(',', ' ')
        parts = normalized.split()
        month = None
        day = None
        year = None

        for word in parts:
            if word in month_names:
                month = month_names[word]
            elif word.isdigit() and 1 <= int(word) <= 31:
                day = int(word)
            elif word in ordinals:
                day = ordinals[word]
            elif len(word) == 4 and word.isdigit():
                year = int(word)

        if month and day:
            if year is None:
                candidate = dt.date(today.year, month, day)
                if candidate < today:
                    candidate = dt.date(today.year + 1, month, day)
                parsed_date = candidate
            else:
                parsed_date = dt.date(year, month, day)
            return DateParseResponse(
                date=parsed_date.isoformat(),
                day_name=parsed_date.strftime("%A")
            )

        raise HTTPException(status_code=400, detail=f"Could not parse date: {date_str}. Try saying 'Thursday', 'April 15', or a date in YYYY-MM-DD format")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Debug endpoint to see all appointments
@app.get("/debug/all_appointments/")
def debug_all_appointments(db: Session = Depends(get_db)):
    """Debug endpoint - shows ALL appointments regardless of date or cancellation status"""
    result = db.execute(select(Appointment))
    appointments = result.scalars().all()
    
    summary = {
        "total_count": len(appointments),
        "by_date": {},
        "appointments": []
    }
    
    for appt in appointments:
        # Count by date
        if appt.date not in summary["by_date"]:
            summary["by_date"][appt.date] = 0
        summary["by_date"][appt.date] += 1
        
        # Add to list
        summary["appointments"].append({
            "id": appt.id,
            "patient_name": appt.patient_name,
            "date": appt.date,
            "token": appt.token_number,
            "canceled": appt.canceled
        })
    
    return summary

# schedule appt
@app.post("/schedule_appointment/")
def schedule_appointment(request: AppointmentRequest, db: Session = Depends(get_db)):
    # Generate next token number for the date
    result = db.execute(
        select(func.max(Appointment.token_number))
        .where(Appointment.date == request.date)
    )
    max_token = result.scalar()
    next_token = (max_token or 0) + 1

    if next_token > 30:
        raise HTTPException(
            status_code=400,
            detail="Sorry, all the appointments for this date are booked. Do you want your appointment on another day?"
        )
    
    if not request.patient_phone:
        raise HTTPException(status_code=400, detail="Patient phone number is required for booking.")

    normalized_name = normalize_name(request.patient_name)
    normalized_phone = normalize_phone(request.patient_phone)

    new_appointment = Appointment(
            patient_name=normalized_name,
            patient_phone=normalized_phone,
            purpose=request.purpose,
            patient_age=request.patient_age,
            patient_gender=request.patient_gender,
            date=request.date,
            token_number=next_token,
        )
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)
    new_appointment_return_obj = AppointmentResponse(
        id = new_appointment.id,
        patient_name= new_appointment.patient_name,
        patient_phone=new_appointment.patient_phone,
        purpose=new_appointment.purpose,
        patient_age=new_appointment.patient_age,
        patient_gender=new_appointment.patient_gender,
        date=new_appointment.date,
        token_number=new_appointment.token_number,
        canceled=new_appointment.canceled,
        created_at=new_appointment.created_at
    )
    return new_appointment_return_obj


# cancel appt
from sqlalchemy import select
@app.post("/cancel_appointment/")
def cancel_appointment(request: CancelAppointmentRequest, db: Session = Depends(get_db)):
    if not request.patient_phone and not request.patient_name:
        raise HTTPException(status_code=400, detail="Provide either patient_phone or patient_name to cancel an appointment.")

    query = select(Appointment).where(Appointment.date == request.date.isoformat()).where(Appointment.canceled == False)

    if request.patient_phone:
        normalized_phone = normalize_phone(request.patient_phone)
        query = query.where(Appointment.patient_phone == normalized_phone)
    else:
        normalized_name = normalize_name(request.patient_name)
        query = query.where(Appointment.patient_name == normalized_name)

    result = db.execute(query)
    appointments = result.scalars().all()

    if not appointments and request.patient_name:
        normalized_name = normalize_name(request.patient_name)
        all_appointments = db.execute(
            select(Appointment)
            .where(Appointment.date == request.date.isoformat())
            .where(Appointment.canceled == False)
        ).scalars().all()
        names = [appt.patient_name for appt in all_appointments]
        close_matches = difflib.get_close_matches(normalized_name, names, n=1, cutoff=0.75)
        if close_matches:
            suggestion = close_matches[0]
            raise HTTPException(
                status_code=404,
                detail=(f"No exact match found for '{request.patient_name}'. "
                        f"Did you mean '{suggestion}'? Please retry with the corrected name or provide the patient's phone number.")
            )

        raise HTTPException(status_code=404, detail="No matching appointment for the provided details found in our system.")

    for appointment in appointments:
        appointment.canceled = True
    
    db.commit()
    
    return CancelAppointmentResponse(canceled_count=len(appointments))

# list appt
@app.get("/list_appointments/")
def list_appointments(date: dt.date = Query(...), db: Session = Depends(get_db)):
    
    result = db.execute(
        select(Appointment)
        .where(Appointment.canceled == False)
        .where(Appointment.date == date.isoformat())
        .order_by(Appointment.token_number.asc())
    )
    booked_appointments = []
    for appointment in result.scalars().all():
        appointment_obj = AppointmentResponse(
        id=appointment.id,
        patient_name=appointment.patient_name,
        patient_phone=appointment.patient_phone,
        purpose=appointment.purpose,
        patient_age=appointment.patient_age,
        patient_gender=appointment.patient_gender,
        date=appointment.date,
        token_number=appointment.token_number,
        canceled=appointment.canceled,
        created_at=appointment.created_at
    )
        booked_appointments.append(appointment_obj)

    return booked_appointments

import uvicorn
if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=4444, reload=True)