"""
=============================================================================
AI MINERAL INTELLIGENCE — FIELD VERIFICATION FEEDBACK SYSTEM
=============================================================================
Module: backend.app.field_verification_service.py

Purpose:
  Provides persistent, audit-logged field observation storage, verification
  workflows, photo attachment management, laboratory assay records, and
  spatially separated model-vs-observation feedback.

Scientific & Data Integrity Rules:
  1. Field observations are recorded separately from model predictions.
  2. Submitting an observation does NOT automatically mark it scientifically verified.
  3. Controlled verification status workflow:
     DRAFT -> SUBMITTED -> UNDER_REVIEW -> (VERIFIED | REJECTED | NEEDS_MORE_EVIDENCE)
  4. Unverified records can NEVER silently become model training labels.
  5. Even VERIFIED records require formal quality-control, deduplication, and
     spatial block isolation before contributing to curated training datasets.
  6. Persistent SQLite storage ensures records survive server restarts.
  7. Strict coordinate validation (lat -90 to 90, lon -180 to 180), safe file handling,
     and path-traversal prevention.
=============================================================================
"""

import os
import sys
import uuid
import math
import sqlite3
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Base directories
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "field_verification.db")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads", "observations")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Controlled status transitions
VALID_STATUSES = {
    "DRAFT",
    "SUBMITTED",
    "UNDER_REVIEW",
    "VERIFIED",
    "REJECTED",
    "NEEDS_MORE_EVIDENCE"
}

STATUS_TRANSITIONS = {
    "DRAFT": ["SUBMITTED"],
    "SUBMITTED": ["UNDER_REVIEW", "REJECTED", "NEEDS_MORE_EVIDENCE", "DRAFT"],
    "UNDER_REVIEW": ["VERIFIED", "REJECTED", "NEEDS_MORE_EVIDENCE", "SUBMITTED"],
    "VERIFIED": ["UNDER_REVIEW"],  # Allowed for re-audit
    "REJECTED": ["SUBMITTED", "DRAFT"],
    "NEEDS_MORE_EVIDENCE": ["SUBMITTED", "UNDER_REVIEW", "DRAFT"]
}

VALID_OBSERVATION_TYPES = {
    "outcrop",
    "rock_sample",
    "soil_sample",
    "drill_core",
    "stream_sediment",
    "trench_exposure",
    "other"
}

ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_PHOTO_MIMES = {"image/jpeg", "image/png", "image/webp"}
MAX_PHOTO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class FieldVerificationService:
    """
    Persistent SQLite storage and workflow service for field observations.
    """

    _initialized = False

    @classmethod
    def get_connection(cls) -> sqlite3.Connection:
        """Returns SQLite connection with row_factory enabled and foreign keys on."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @classmethod
    def initialize_db(cls) -> None:
        """Initializes database schema and tables if they do not exist."""
        if cls._initialized:
            return

        with cls.get_connection() as conn:
            cursor = conn.cursor()

            # Observations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id TEXT PRIMARY KEY,
                    latitude REAL NOT NULL CHECK(latitude >= -90.0 AND latitude <= 90.0),
                    longitude REAL NOT NULL CHECK(longitude >= -180.0 AND longitude <= 180.0),
                    crs TEXT NOT NULL DEFAULT 'EPSG:4326 - WGS 84',
                    observation_timestamp TEXT NOT NULL,
                    mineral TEXT NOT NULL,
                    observation_type TEXT NOT NULL,
                    sample_id TEXT,
                    rock_soil_description TEXT NOT NULL,
                    geological_characteristics TEXT NOT NULL,
                    observer_name TEXT NOT NULL,
                    observer_organization TEXT,
                    verification_status TEXT NOT NULL DEFAULT 'DRAFT',
                    status_notes TEXT,
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    general_notes TEXT,
                    analysis_id TEXT,
                    training_eligible INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Photos table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observation_photos (
                    id TEXT PRIMARY KEY,
                    observation_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    mime_type TEXT NOT NULL,
                    caption TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE CASCADE
                )
            """)

            # Laboratory Assays table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observation_assays (
                    id TEXT PRIMARY KEY,
                    observation_id TEXT NOT NULL,
                    element_or_compound TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    laboratory_name TEXT,
                    report_reference TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE CASCADE
                )
            """)

            # Audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS verification_audit_log (
                    id TEXT PRIMARY KEY,
                    observation_id TEXT NOT NULL,
                    previous_status TEXT,
                    new_status TEXT NOT NULL,
                    changed_by TEXT NOT NULL,
                    reason TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE CASCADE
                )
            """)

            # Indexes for fast spatial and filtering queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_coords ON observations(latitude, longitude)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_mineral ON observations(mineral)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_status ON observations(verification_status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_date ON observations(observation_timestamp)")

            conn.commit()

        cls._initialized = True

    # -------------------------------------------------------------------------
    # Observation CRUD
    # -------------------------------------------------------------------------
    @classmethod
    def create_observation(cls, data: Dict[str, Any], user_role: str = "geologist") -> Dict[str, Any]:
        """
        Creates a new persistent field observation.
        """
        cls.initialize_db()

        lat = float(data.get("latitude"))
        lon = float(data.get("longitude"))
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude {lat} is out of bounds [-90, 90].")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"Longitude {lon} is out of bounds [-180, 180].")

        mineral = str(data.get("mineral", "")).strip()
        if not mineral:
            raise ValueError("Mineral or geological material is required.")

        obs_type = str(data.get("observation_type", "outcrop")).strip().lower()
        if obs_type not in VALID_OBSERVATION_TYPES:
            obs_type = "outcrop"

        description = str(data.get("rock_soil_description", "")).strip()
        if not description:
            raise ValueError("Rock or soil description is required.")

        geol_chars = str(data.get("geological_characteristics", "")).strip()
        if not geol_chars:
            geol_chars = "No specific structural features noted."

        observer_name = str(data.get("observer_name", "")).strip()
        if not observer_name:
            observer_name = "Field Observer (Unspecified)"

        obs_timestamp = data.get("observation_timestamp")
        if not obs_timestamp:
            obs_timestamp = datetime.now(timezone.utc).isoformat()

        # Status rules: new observation defaults to DRAFT or SUBMITTED
        desired_status = str(data.get("verification_status", "DRAFT")).strip().upper()
        if desired_status not in ("DRAFT", "SUBMITTED"):
            desired_status = "SUBMITTED" if desired_status == "SUBMITTED" else "DRAFT"

        obs_id = f"OBS-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO observations (
                    id, latitude, longitude, crs, observation_timestamp,
                    mineral, observation_type, sample_id, rock_soil_description,
                    geological_characteristics, observer_name, observer_organization,
                    verification_status, status_notes, general_notes, analysis_id,
                    training_eligible, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs_id,
                lat,
                lon,
                data.get("crs", "EPSG:4326 - WGS 84"),
                obs_timestamp,
                mineral,
                obs_type,
                data.get("sample_id"),
                description,
                geol_chars,
                observer_name,
                data.get("observer_organization"),
                desired_status,
                data.get("status_notes", "Initial record created."),
                data.get("general_notes"),
                data.get("analysis_id"),
                0,  # Never training eligible initially
                now_iso,
                now_iso
            ))

            # Audit log entry
            log_id = f"LOG-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO verification_audit_log (
                    id, observation_id, previous_status, new_status,
                    changed_by, reason, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id,
                obs_id,
                None,
                desired_status,
                observer_name,
                "Initial creation of observation record",
                now_iso
            ))

            # Optional inline assays
            assays = data.get("assays") or []
            for assay in assays:
                if assay.get("element_or_compound") and assay.get("value") is not None:
                    assay_id = f"ASY-{uuid.uuid4().hex[:8]}"
                    cursor.execute("""
                        INSERT INTO observation_assays (
                            id, observation_id, element_or_compound, value,
                            unit, laboratory_name, report_reference, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        assay_id,
                        obs_id,
                        str(assay["element_or_compound"]),
                        float(assay["value"]),
                        str(assay.get("unit", "%")),
                        assay.get("laboratory_name"),
                        assay.get("report_reference"),
                        now_iso
                    ))

            conn.commit()

        return cls.get_observation_by_id(obs_id)

    @classmethod
    def get_observation_by_id(cls, obs_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single observation by ID, including its photos, assays, and audit history."""
        cls.initialize_db()

        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM observations WHERE id = ?", (obs_id,))
            row = cursor.fetchone()
            if not row:
                return None

            obs = dict(row)

            # Photos
            cursor.execute("SELECT * FROM observation_photos WHERE observation_id = ? ORDER BY created_at ASC", (obs_id,))
            obs["photos"] = [dict(r) for r in cursor.fetchall()]

            # Assays
            cursor.execute("SELECT * FROM observation_assays WHERE observation_id = ? ORDER BY created_at ASC", (obs_id,))
            obs["assays"] = [dict(r) for r in cursor.fetchall()]

            # Audit log
            cursor.execute("SELECT * FROM verification_audit_log WHERE observation_id = ? ORDER BY timestamp DESC", (obs_id,))
            obs["audit_log"] = [dict(r) for r in cursor.fetchall()]

            return obs

    @classmethod
    def list_observations(
        cls,
        mineral: Optional[str] = None,
        verification_status: Optional[str] = None,
        observation_type: Optional[str] = None,
        search_query: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius_km: Optional[float] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Lists observations with optional spatial proximity, mineral, status, and type filtering.
        """
        cls.initialize_db()

        conditions = []
        params = []

        if mineral and mineral.lower() != "all":
            conditions.append("LOWER(mineral) = LOWER(?)")
            params.append(mineral.strip())

        if verification_status and verification_status.lower() != "all":
            conditions.append("UPPER(verification_status) = UPPER(?)")
            params.append(verification_status.strip())

        if observation_type and observation_type.lower() != "all":
            conditions.append("LOWER(observation_type) = LOWER(?)")
            params.append(observation_type.strip())

        if search_query:
            conditions.append("(rock_soil_description LIKE ? OR geological_characteristics LIKE ? OR id LIKE ? OR observer_name LIKE ?)")
            q = f"%{search_query.strip()}%"
            params.extend([q, q, q, q])

        # Bounding box rough filter if radius specified
        if lat is not None and lon is not None and radius_km is not None and radius_km > 0:
            deg_lat = radius_km / 111.0
            deg_lon = radius_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
            conditions.append("latitude BETWEEN ? AND ?")
            params.extend([lat - deg_lat, lat + deg_lat])
            conditions.append("longitude BETWEEN ? AND ?")
            params.extend([lon - deg_lon, lon + deg_lon])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with cls.get_connection() as conn:
            cursor = conn.cursor()

            # Count total
            cursor.execute(f"SELECT COUNT(*) as total FROM observations {where_clause}", params)
            total_count = cursor.fetchone()["total"]

            # Query items
            query = f"""
                SELECT * FROM observations
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            cursor.execute(query, params + [limit, offset])
            rows = [dict(r) for r in cursor.fetchall()]

            # Calculate accurate great-circle distance if lat/lon provided
            if lat is not None and lon is not None:
                for row in rows:
                    d_lat = math.radians(row["latitude"] - lat)
                    d_lon = math.radians(row["longitude"] - lon)
                    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(row["latitude"])) * math.sin(d_lon / 2) ** 2
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                    row["distance_km"] = round(6371.0 * c, 2)

                # Filter strictly within radius if requested
                if radius_km is not None and radius_km > 0:
                    rows = [r for r in rows if r.get("distance_km", 999999) <= radius_km]
                    rows.sort(key=lambda x: x.get("distance_km", 0))

            # Fetch photo counts and primary photo
            for row in rows:
                cursor.execute("SELECT COUNT(*) as cnt FROM observation_photos WHERE observation_id = ?", (row["id"],))
                row["photos_count"] = cursor.fetchone()["cnt"]
                cursor.execute("SELECT COUNT(*) as cnt FROM observation_assays WHERE observation_id = ?", (row["id"],))
                row["assays_count"] = cursor.fetchone()["cnt"]

            return {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "returned": len(rows),
                "observations": rows
            }

    @classmethod
    def update_observation(
        cls,
        obs_id: str,
        data: Dict[str, Any],
        user_role: str = "geologist"
    ) -> Dict[str, Any]:
        """
        Updates an existing observation's descriptive fields.
        """
        cls.initialize_db()
        existing = cls.get_observation_by_id(obs_id)
        if not existing:
            raise ValueError(f"Observation {obs_id} not found.")

        # If already VERIFIED, non-reviewers cannot modify descriptive data
        if existing["verification_status"] == "VERIFIED" and user_role not in ("reviewer", "admin"):
            raise PermissionError("Cannot edit verified observation without reviewer authorization.")

        allowed_fields = [
            "rock_soil_description",
            "geological_characteristics",
            "sample_id",
            "general_notes",
            "status_notes",
            "observer_organization"
        ]

        updates = []
        params = []
        for f in allowed_fields:
            if f in data:
                updates.append(f"{f} = ?")
                params.append(data[f])

        if not updates:
            return existing

        now_iso = datetime.now(timezone.utc).isoformat()
        updates.append("updated_at = ?")
        params.append(now_iso)
        params.append(obs_id)

        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE observations SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

        return cls.get_observation_by_id(obs_id)

    @classmethod
    def change_verification_status(
        cls,
        obs_id: str,
        new_status: str,
        changed_by: str,
        reason: str,
        user_role: str = "reviewer"
    ) -> Dict[str, Any]:
        """
        Executes a controlled verification status transition with audit log recording.
        """
        cls.initialize_db()
        existing = cls.get_observation_by_id(obs_id)
        if not existing:
            raise ValueError(f"Observation {obs_id} not found.")

        current_status = existing["verification_status"]
        new_status = new_status.strip().upper()

        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'. Allowed: {', '.join(sorted(VALID_STATUSES))}.")

        # Role checks: only reviewer or admin can mark VERIFIED or REJECTED
        if new_status in ("VERIFIED", "REJECTED") and user_role not in ("reviewer", "admin"):
            raise PermissionError(f"Role '{user_role}' cannot change status to {new_status}. Reviewer authorization required.")

        allowed_targets = STATUS_TRANSITIONS.get(current_status, [])
        if new_status not in allowed_targets and new_status != current_status:
            raise ValueError(
                f"Illegal status transition from {current_status} to {new_status}. "
                f"Permitted transitions from {current_status}: {', '.join(allowed_targets)}."
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        training_eligible = 1 if (new_status == "VERIFIED" and len(existing.get("assays", [])) > 0) else 0

        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE observations SET
                    verification_status = ?,
                    status_notes = ?,
                    reviewed_by = ?,
                    reviewed_at = ?,
                    training_eligible = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                new_status,
                reason,
                changed_by if new_status in ("VERIFIED", "REJECTED", "UNDER_REVIEW") else existing.get("reviewed_by"),
                now_iso if new_status in ("VERIFIED", "REJECTED") else existing.get("reviewed_at"),
                training_eligible,
                now_iso,
                obs_id
            ))

            log_id = f"LOG-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO verification_audit_log (
                    id, observation_id, previous_status, new_status,
                    changed_by, reason, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id,
                obs_id,
                current_status,
                new_status,
                changed_by,
                reason,
                now_iso
            ))

            conn.commit()

        return cls.get_observation_by_id(obs_id)

    # -------------------------------------------------------------------------
    # Photograph Management
    # -------------------------------------------------------------------------
    @classmethod
    def attach_photo(
        cls,
        obs_id: str,
        file_bytes: bytes,
        original_filename: str,
        mime_type: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Safely saves an uploaded photograph with UUID filename, type and size checks.
        """
        cls.initialize_db()
        existing = cls.get_observation_by_id(obs_id)
        if not existing:
            raise ValueError(f"Observation {obs_id} not found.")

        if len(file_bytes) == 0:
            raise ValueError("Uploaded photo file is empty.")
        if len(file_bytes) > MAX_PHOTO_SIZE_BYTES:
            raise ValueError(f"File size {len(file_bytes)/(1024*1024):.1f}MB exceeds 10MB limit.")

        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in ALLOWED_PHOTO_EXTENSIONS or mime_type not in ALLOWED_PHOTO_MIMES:
            raise ValueError(f"Invalid photo format '{mime_type}' with extension '{ext}'. Only JPEG, PNG, and WebP are permitted.")

        photo_id = f"PHT-{uuid.uuid4().hex[:8]}"
        safe_filename = f"{photo_id}{ext}"
        target_path = os.path.join(UPLOADS_DIR, safe_filename)

        # Path traversal guard
        common = os.path.commonpath([os.path.abspath(target_path), os.path.abspath(UPLOADS_DIR)])
        if common != os.path.abspath(UPLOADS_DIR):
            raise ValueError("Invalid target filename: path traversal detected.")

        with open(target_path, "wb") as f:
            f.write(file_bytes)

        now_iso = datetime.now(timezone.utc).isoformat()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO observation_photos (
                    id, observation_id, filename, original_filename,
                    file_size_bytes, mime_type, caption, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                photo_id,
                obs_id,
                safe_filename,
                os.path.basename(original_filename),
                len(file_bytes),
                mime_type,
                caption,
                now_iso
            ))
            conn.commit()

        return {
            "id": photo_id,
            "observation_id": obs_id,
            "filename": safe_filename,
            "original_filename": original_filename,
            "file_size_bytes": len(file_bytes),
            "mime_type": mime_type,
            "caption": caption,
            "created_at": now_iso
        }

    @classmethod
    def get_photo_path(cls, filename: str) -> Optional[str]:
        """Returns safe absolute path to a photo file or None if missing."""
        clean_name = os.path.basename(filename)
        path = os.path.join(UPLOADS_DIR, clean_name)
        if os.path.exists(path):
            return path
        return None

    # -------------------------------------------------------------------------
    # Assay Management
    # -------------------------------------------------------------------------
    @classmethod
    def add_assay(
        cls,
        obs_id: str,
        element_or_compound: str,
        value: float,
        unit: str = "%",
        laboratory_name: Optional[str] = None,
        report_reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """Adds a laboratory chemical assay result to an observation."""
        cls.initialize_db()
        existing = cls.get_observation_by_id(obs_id)
        if not existing:
            raise ValueError(f"Observation {obs_id} not found.")

        assay_id = f"ASY-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO observation_assays (
                    id, observation_id, element_or_compound, value,
                    unit, laboratory_name, report_reference, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assay_id,
                obs_id,
                element_or_compound.strip(),
                float(value),
                unit.strip(),
                laboratory_name,
                report_reference,
                now_iso
            ))
            conn.commit()

        return {
            "id": assay_id,
            "observation_id": obs_id,
            "element_or_compound": element_or_compound,
            "value": float(value),
            "unit": unit,
            "laboratory_name": laboratory_name,
            "report_reference": report_reference,
            "created_at": now_iso
        }

    # -------------------------------------------------------------------------
    # Spatial Comparison: Field Observation vs Model Outputs
    # -------------------------------------------------------------------------
    @classmethod
    def compare_with_model(
        cls,
        obs_id: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius_km: float = 10.0
    ) -> Dict[str, Any]:
        """
        Compares an observation with platform model predictions and satellite evidence.
        Strictly distinguishes field findings from model inferences.
        """
        obs = cls.get_observation_by_id(obs_id)
        if not obs:
            raise ValueError(f"Observation {obs_id} not found.")

        obs_lat = obs["latitude"]
        obs_lon = obs["longitude"]
        mineral = obs["mineral"]

        # Check if model exists for this mineral
        from backend.app.mineral_service import (
            is_within_tile,
            calculate_manganese_prospectivity
        )

        in_t44qmk = is_within_tile(obs_lat, obs_lon)
        has_validated_model = (mineral.lower() == "manganese" and in_t44qmk)

        model_output = None
        if has_validated_model:
            calc = calculate_manganese_prospectivity(obs_lat, obs_lon, radius_km)
            model_output = {
                "model_available": True,
                "model_name": "Sentinel-2 MSI Random Forest Manganese Classifier",
                "prospectivity_score_pct": calc["score_pct"],
                "classification": calc["classification"],
                "candidate_zone": calc["candidate_zone"]
            }
        else:
            model_output = {
                "model_available": False,
                "model_name": f"{mineral} Spatial Pipeline",
                "prospectivity_score_pct": None,
                "classification": "WITHHELD_NO_VALIDATED_MODEL" if mineral.lower() != "manganese" else "OUTSIDE_TRAINING_FOOTPRINT",
                "reason": (
                    f"Target is outside Tile T44QMK training footprint."
                    if mineral.lower() == "manganese" else
                    f"No validated spatial ML model exists for {mineral}. Optical data cannot prove subsurface ore."
                )
            }

        # Scientific comparison interpretation
        assays = obs.get("assays", [])
        has_assays = len(assays) > 0
        status = obs["verification_status"]

        alignment_note = (
            f"Observation ({obs['observation_type']}, status={status}) records: '{obs['rock_soil_description'][:100]}...'. "
            f"Model status: {model_output['classification']}. "
            f"Assays: {len(assays)} laboratory records attached."
        )

        training_curation_status = {
            "eligible_for_future_training": obs.get("training_eligible", 0) == 1,
            "requires_independent_qc": True,
            "leakage_prevention": "Spatial block holdout required before inclusion in any retrained model",
            "disclaimer": "Unverified and reviewed field records are NOT automatically fed into active models."
        }

        return {
            "observation_id": obs_id,
            "observation_metadata": {
                "mineral": mineral,
                "coordinates": {"latitude": obs_lat, "longitude": obs_lon},
                "observation_type": obs["observation_type"],
                "verification_status": status,
                "observer": obs["observer_name"],
                "timestamp": obs["observation_timestamp"]
            },
            "field_evidence_summary": {
                "description": obs["rock_soil_description"],
                "characteristics": obs["geological_characteristics"],
                "assays": assays,
                "photos_count": len(obs.get("photos", []))
            },
            "model_comparison": model_output,
            "comparison_synthesis": alignment_note,
            "training_curation_policy": training_curation_status
        }

    # -------------------------------------------------------------------------
    # GeoJSON Export
    # -------------------------------------------------------------------------
    @classmethod
    def export_geojson(
        cls,
        mineral: Optional[str] = None,
        verification_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exports observations as standard GeoJSON FeatureCollection."""
        result = cls.list_observations(mineral=mineral, verification_status=verification_status, limit=1000)
        features = []

        for obs in result["observations"]:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [obs["longitude"], obs["latitude"]]
                },
                "properties": {
                    "id": obs["id"],
                    "mineral": obs["mineral"],
                    "observation_type": obs["observation_type"],
                    "verification_status": obs["verification_status"],
                    "observer_name": obs["observer_name"],
                    "observer_organization": obs["observer_organization"],
                    "sample_id": obs["sample_id"],
                    "rock_soil_description": obs["rock_soil_description"],
                    "geological_characteristics": obs["geological_characteristics"],
                    "observation_timestamp": obs["observation_timestamp"],
                    "photos_count": obs.get("photos_count", 0),
                    "assays_count": obs.get("assays_count", 0)
                }
            }
            features.append(feature)

        return {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
            },
            "features": features
        }
