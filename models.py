# backend/models.py
from pydantic import BaseModel, EmailStr, field_validator, Field
from datetime import datetime
from typing import Optional
import re

class User(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "user"  # New field: 'user' or 'admin'

    @field_validator('password')
    def password_strength(cls, value):
        if len(value) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', value):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', value):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', value): 
           raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValueError('Password must contain at least one special character')
        return value

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Schema for updating user details
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None

class PasswordChange(BaseModel):
    old_password: str
    new_password: str
    
    @field_validator('new_password')
    def password_strength(cls, value):
        # Re-use logic or import it, duplicating for brevity here
        if len(value) < 8: raise ValueError('Password too short')
        return value

# Output schema to hide password
class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str

class ShipmentCreate(BaseModel):
    shipment_number: str
    container_number: str
    route_details: str
    goods_type: str
    device: str
    expected_delivery_date: datetime 
    po_number: str
    delivery_number: str
    ndc_number: str
    batch_id: str
    serial_number_of_goods: str
    shipment_description: str

class DeviceData(BaseModel):
    DeviceId: str
    BatteryLevel: float
    FirstSensortemperature: str 
    RouteFrom: str
    RouteTo: str
    Timestamp: datetime