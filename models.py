from typing import Any, Optional, List, Dict
from datetime import datetime
from bson import ObjectId
import re # Imported for Regex validation

from pydantic import (
    BaseModel, 
    EmailStr, 
    Field, 
    GetCoreSchemaHandler, 
    GetJsonSchemaHandler,
    field_validator
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

# ==========================================
# 1. HELPERS (ObjectId)
# ==========================================

class PyObjectId(str):
    """
    Custom type for handling MongoDB ObjectIds in Pydantic V2.
    """
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ]),
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return handler(core_schema.str_schema())


# ==========================================
# 2. VALIDATION LOGIC (Reusable)
# ==========================================

def validate_strong_password(v: str) -> str:
    """
    Validates that password has:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one digit
    """
    if len(v) < 8:
        raise ValueError('Password must be at least 8 characters long')
    if not re.search(r'[A-Z]', v):
        raise ValueError('Password must contain at least one uppercase letter')
    if not re.search(r'\d', v):
        raise ValueError('Password must contain at least one number')
    return v

# ==========================================
# 3. USER MODELS
# ==========================================

class UserIn(BaseModel):
    """Input model for registering a new user."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str
    full_name: Optional[str] = Field(None, min_length=1)

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Username cannot be empty or whitespace")
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("Username must contain only letters, numbers, and underscores")
        return v

    @field_validator('password')
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        return validate_strong_password(v)


class UserOut(BaseModel):
    """Output model for user details."""
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    username: Optional[str] = None
    full_name: Optional[str] = None
    email: EmailStr
    is_active: bool = True
    is_admin: bool = False

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }

# Aliases used by your routes
UserPublic = UserOut

class UpdateUser(BaseModel):
    """Input model for updating user profile."""
    full_name: Optional[str] = Field(None, min_length=1)
    email: Optional[EmailStr] = None
    password: Optional[str] = None

    @field_validator('password')
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        if v is None:
            return v
        return validate_strong_password(v)


class ChangePasswordIn(BaseModel):
    """Input model for changing password."""
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        return validate_strong_password(v)


# ==========================================
# 4. AUTH & TOKEN MODELS
# ==========================================

class TokenResponse(BaseModel):
    """Schema for the login response containing tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    # expires_in is optional in response, usually calculated by client, 
    # but if you want to send it:
    expires_in: Optional[int] = None 

Token = TokenResponse

class TokenData(BaseModel):
    """Schema for data extracted from a JWT token."""
    username: Optional[str] = None
    user_id: Optional[str] = None

class SessionOut(BaseModel):
    """Schema for tracking active refresh token sessions."""
    session_id: Optional[str] = Field(alias="_id", default=None)
    user_id: PyObjectId
    created_at: datetime
    expires_at: datetime
    is_revoked: bool = False
    device: Optional[str] = "Unknown"
    ip: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


# ==========================================
# 5. SHIPMENT MODELS
# ==========================================

class ShipmentIn(BaseModel):
    """Input model for creating a shipment."""
    recipient_name: str = Field(..., min_length=2)
    recipient_address: str = Field(..., min_length=5)
    city: str
    postal_code: str
    items: List[str] = []
    weight_kg: float = 0.0
    associated_shipment_id: Optional[str] = None # Added for linking logic

    @field_validator('weight_kg')
    @classmethod
    def validate_weight(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Weight must be greater than 0")
        return v

    @field_validator('items')
    @classmethod
    def validate_items(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Shipment must contain at least one item")
        return v


class ShipmentOut(BaseModel):
    """Output model for viewing a shipment."""
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: Optional[PyObjectId] = Field(alias="created_by", default=None)
    recipient_name: str
    recipient_address: str
    city: Optional[str] = None
    postal_code: Optional[str] = None
    items: List[str] = []
    weight_kg: float = 0.0
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    associated_shipment_id: Optional[PyObjectId] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }


# ==========================================
# 6. DEVICE DATA MODELS
# ==========================================

class DeviceDataIn(BaseModel):
    """Input model for sending device telemetry."""
    device_id: str = Field(..., min_length=1)
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    location: Optional[str] = None
    battery_level: Optional[float] = None
    extra_info: Optional[Dict[str, Any]] = None

    @field_validator('battery_level')
    @classmethod
    def validate_battery(cls, v: float) -> float:
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Battery level must be between 0 and 100")
        return v

class DeviceDataOut(BaseModel):
    """Output model for viewing device data."""
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    device_id: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    location: Optional[str] = None
    battery_level: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }