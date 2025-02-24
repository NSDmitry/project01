from fastapi import APIRouter, Depends

from services.SSO.Models import SingUpRequestModel, SignInRequestModel
from services.SSO.SSOService import SSOService

router = APIRouter(prefix="/api/SSO", tags=["SSO"])

@router.post("/signup")
def sign_up(model: SingUpRequestModel, sso_service: SSOService = Depends()):
    return sso_service.sign_up(model=model)

@router.post("/signin")
def sign_in(model: SignInRequestModel, sso_service: SSOService = Depends()):
    return sso_service.sign_in(model=model)