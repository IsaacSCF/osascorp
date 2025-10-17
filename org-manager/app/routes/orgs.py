from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import io
import json
from app.database import get_db
from app.models.orgs import Org
from app.models.audit import AuditLog
from app.schemas.orgs import OrgCreate, OrgUpdate, OrgResponse
from app.schemas.audit import AuditLogResponse
from app.utils.auth import get_current_active_user, check_role, check_org_type_access
from app.utils.broadcast import manager
from app.utils.security import sanitize_input
from app.models.users import User

router = APIRouter()

def log_audit_action(db: Session, user_id: int, action: str, target_table: str, target_id: int, details: str = None):
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        target_table=target_table,
        target_id=target_id,
        details=details
    )
    db.add(audit_log)
    db.commit()

@router.get("/", response_model=List[OrgResponse])
def read_orgs(
    skip: int = 0,
    limit: int = 100,
    tipo: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(Org)
    if tipo:
        query = query.filter(Org.tipo == tipo)
    orgs = query.offset(skip).limit(limit).all()

    # Convert tags_fabricacao from JSON string to list for response
    for org in orgs:
        if org.tags_fabricacao:
            try:
                org.tags_fabricacao = json.loads(org.tags_fabricacao)
            except:
                org.tags_fabricacao = []

    return orgs

@router.get("/{org_id}", response_model=OrgResponse)
def read_org(org_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    org = db.query(Org).filter(Org.id == org_id).first()
    if org is None:
        raise HTTPException(status_code=404, detail="Org not found")

    # Convert tags_fabricacao from JSON string to list for response
    if org.tags_fabricacao:
        try:
            org.tags_fabricacao = json.loads(org.tags_fabricacao)
        except:
            org.tags_fabricacao = []

    return org

@router.post("/", response_model=OrgResponse)
async def create_org(
    org: OrgCreate,
    current_user: User = Depends(check_role("moderador")),
    db: Session = Depends(get_db)
):
    # Sanitize inputs
    org.faccao = sanitize_input(org.faccao)
    if org.contato:
        org.contato = sanitize_input(org.contato)
    if org.discord_lider:
        org.discord_lider = sanitize_input(org.discord_lider)

    # Convert tags_fabricacao list to JSON string for storage
    org_data = org.dict()
    if org_data.get('tags_fabricacao'):
        # Ensure it's a list before JSON encoding
        tags = org_data['tags_fabricacao']
        if isinstance(tags, list):
            org_data['tags_fabricacao'] = json.dumps(tags)
        else:
            org_data['tags_fabricacao'] = json.dumps([tags]) if tags else None
    else:
        org_data['tags_fabricacao'] = None

    db_org = Org(**org_data)
    db.add(db_org)
    db.commit()
    db.refresh(db_org)

    # Log audit
    log_audit_action(db, current_user.id, "create", "orgs", db_org.id, f"Created org: {db_org.faccao}")

    # Broadcast
    await manager.publish_event("org_created", {"id": db_org.id, "faccao": db_org.faccao})

    return db_org

@router.put("/{org_id}", response_model=OrgResponse)
async def update_org(
    org_id: int,
    org_update: OrgUpdate,
    current_user: User = Depends(check_role("moderador")),
    db: Session = Depends(get_db)
):
    org = db.query(Org).filter(Org.id == org_id).first()
    if org is None:
        raise HTTPException(status_code=404, detail="Org not found")

    update_data = org_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field in ["faccao", "contato", "discord_lider"]:
            value = sanitize_input(value)
        elif field == "tags_fabricacao" and value is not None:
            value = json.dumps(value) if isinstance(value, list) else value
        setattr(org, field, value)

    db.commit()
    db.refresh(org)

    # Log audit
    details = f"Updated org {org.faccao}: {update_data}"
    log_audit_action(db, current_user.id, "update", "orgs", org.id, details)

    # Convert tags_fabricacao from JSON string to list for response
    if org.tags_fabricacao:
        try:
            org.tags_fabricacao = json.loads(org.tags_fabricacao)
        except:
            org.tags_fabricacao = []

    # Broadcast
    await manager.publish_event("org_updated", {"id": org.id, **update_data})

    return org

@router.delete("/{org_id}")
async def delete_org(
    org_id: int,
    current_user: User = Depends(check_role("moderador")),
    db: Session = Depends(get_db)
):
    org = db.query(Org).filter(Org.id == org_id).first()
    if org is None:
        raise HTTPException(status_code=404, detail="Org not found")

    db.delete(org)
    db.commit()

    # Log audit
    log_audit_action(db, current_user.id, "delete", "orgs", org_id, f"Deleted org: {org.faccao}")

    # Broadcast
    await manager.publish_event("org_deleted", {"id": org_id})

    return {"message": "Org deleted"}

@router.post("/import")
def import_orgs(
    file: UploadFile = File(...),
    current_user: User = Depends(check_role("admin")),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(status_code=400, detail="File must be CSV or Excel")

    contents = file.file.read()
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
    else:
        df = pd.read_excel(io.BytesIO(contents))

    imported_count = 0
    errors = []

    for index, row in df.iterrows():
        try:
            # Process tags_fabricacao from "Fabricação" column
            fabricacao_raw = str(row.get("Fabricação", "")).strip()
            tags_fabricacao = None
            if fabricacao_raw and fabricacao_raw.lower() not in ['nan', '—', '', '-', 'NaN']:
                # Split by "/" or "," and clean up
                tags = [tag.strip() for tag in fabricacao_raw.replace(',', '/').split('/') if tag.strip() and tag.lower() not in ['nan', '—', '', '-', 'NaN']]
                if tags:
                    tags_fabricacao = json.dumps(tags)

            # Helper function to check if value is empty
            def is_empty(val):
                if pd.isna(val):
                    return True
                val_str = str(val).strip()
                return val_str in ['', 'nan', '—', 'NaN', '-']

            # Determine tipo based on tags or default to LEGAL
            tipo = "LEGAL"
            if tags_fabricacao:
                tags_list = json.loads(tags_fabricacao)
                # If any tag suggests illegal activity, mark as ILEGAL
                illegal_keywords = ['arma', 'drogas', 'lavagem', 'contrabando', 'desmanche', 'munição', 'metanfetamina', 'heroína', 'canabis', 'perfume']
                if any(any(keyword in tag.lower() for keyword in illegal_keywords) for tag in tags_list):
                    tipo = "ILEGAL"

            # Parse date with multiple formats
            data_entrega = None
            if not is_empty(row.get("Data da Entrega")):
                date_str = str(row.get("Data da Entrega")).strip()
                try:
                    # Try dd/mm/yyyy format first
                    data_entrega = pd.to_datetime(date_str, format='%d/%m/%Y', dayfirst=True).date()
                except:
                    try:
                        # Try other formats
                        data_entrega = pd.to_datetime(date_str, dayfirst=True).date()
                    except:
                        # If parsing fails, skip date
                        pass

            org_data = {
                "faccao": sanitize_input(str(row.get("Facção", ""))),
                "tags_fabricacao": tags_fabricacao,
                "contato": sanitize_input(str(row.get("Contato", ""))) if not is_empty(row.get("Contato")) else None,
                "membros_ativos": int(float(row.get("Membros Ativos", 0))) if not is_empty(row.get("Membros Ativos")) else None,
                "data_entrega": data_entrega,
                "discord_lider": sanitize_input(str(row.get("Discord Líder", ""))) if not is_empty(row.get("Discord Líder")) else None,
                "tipo": tipo,
                "ativo": True,  # Default to active
                "entregue": False  # Default to not delivered
            }

            # Check if org with same name already exists
            existing_org = db.query(Org).filter(Org.faccao == org_data["faccao"]).first()
            if existing_org:
                errors.append(f"Linha {index + 2}: Organização '{org_data['faccao']}' já existe")
                continue

            db_org = Org(**org_data)
            db.add(db_org)
            imported_count += 1

        except Exception as e:
            errors.append(f"Linha {index + 2}: Erro ao processar - {str(e)}")
            continue

    db.commit()

    # Log audit
    log_audit_action(db, current_user.id, "import", "orgs", 0, f"Imported {imported_count} orgs from file. Errors: {len(errors)}")

    message = f"Imported {imported_count} organizations"
    if errors:
        message += f". Errors: {len(errors)} - " + "; ".join(errors[:5])  # Show first 5 errors

    return {"message": message}

@router.get("/audit/", response_model=List[AuditLogResponse])
def read_audit_logs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(check_role("admin")),
    db: Session = Depends(get_db)
):
    logs = db.query(AuditLog).offset(skip).limit(limit).all()
    return logs
