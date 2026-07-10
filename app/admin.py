"""Protección de las acciones que modifican datos compartidos.

En local se permite editar. En Hugging Face la app es de solo lectura hasta
que el propietario configure ``ADMIN_PASSWORD`` como secret del Space.
"""
from __future__ import annotations

import os
import streamlit as st


def editing_enabled() -> bool:
    public_space = bool(os.getenv("SPACE_ID") or os.getenv("HF_SPACE_ID"))
    if not public_space:
        return True
    secret = os.getenv("ADMIN_PASSWORD")
    try:
        secret = secret or st.secrets.get("ADMIN_PASSWORD")
    except Exception:
        pass
    return bool(secret and st.session_state.get("_admin_ok"))


def editor_gate() -> bool:
    if editing_enabled():
        return True
    secret = os.getenv("ADMIN_PASSWORD")
    try:
        secret = secret or st.secrets.get("ADMIN_PASSWORD")
    except Exception:
        pass
    if not secret:
        st.info("🔒 Modo público: edición desactivada. Configura el secret `ADMIN_PASSWORD` para habilitarla.")
        return False
    with st.popover("🔒 Modo edición"):
        password = st.text_input("Contraseña de administración", type="password")
        if st.button("Desbloquear"):
            if password == secret:
                st.session_state["_admin_ok"] = True
                st.rerun()
            st.error("Contraseña incorrecta.")
    return False
