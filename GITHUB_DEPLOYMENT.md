# GitHub Deployment Guide - QMC Agent

Esta guía te ayudará a subir el proyecto QMC Agent a GitHub de manera segura.

## ✅ Pre-requisitos Completados

- **`.gitignore` actualizado**: Todos los archivos sensibles (credenciales, logs, reportes) están protegidos.
- **`.env.example` presente**: Plantilla de configuración disponible para otros desarrolladores.

---

## 📋 Pasos para Subir a GitHub

### 1. Inicializar Git (si no está inicializado)

Abre la terminal en la carpeta del proyecto y ejecuta:

```bash
cd C:\Users\Lenovo\Documents\agent_qmc
git init
```

### 2. Añadir los archivos al staging area

```bash
git add .
```

> **Nota**: Esto agregará todos los archivos EXCEPTO los especificados en `.gitignore`.

### 3. Crear el primer commit

```bash
git commit -m "Initial commit: QMC Multi-Agent System with LangGraph"
```

### 4. Crear el repositorio en GitHub

1. Ve a [GitHub](https://github.com) e inicia sesión.
2. Haz clic en el botón **"New"** (o **"+"** → **"New repository"**).
3. Completa:
   - **Repository name**: `qmc-agent` (o el nombre que prefieras)
   - **Description**: "AI-powered Qlik task monitoring system using LangGraph and LLaMA 3"
   - **Visibility**: Elige **Private** (recomendado) o **Public**
4. **NO** marques "Initialize with README" (ya tienes uno).
5. Haz clic en **"Create repository"**.

### 5. Conectar tu proyecto local con GitHub

GitHub te mostrará las instrucciones. Usa el método **"push an existing repository"**:

```bash
git remote add origin https://github.com/TU_USUARIO/qmc-agent.git
git branch -M main
git push -u origin main
```

> **Reemplaza** `TU_USUARIO` con tu nombre de usuario de GitHub.

### 6. Verificar

Ve a tu repositorio en GitHub. Deberías ver todos los archivos del proyecto EXCEPTO:
- `.env` (secretos)
- `logs/` (archivos temporales)
- `reportes/` (salidas)
- `browser_state.json`

---

## 🔒 Seguridad: Configurar Secrets en GitHub (Opcional)

Si quieres ejecutar el agente usando GitHub Actions más adelante:

1. Ve a tu repositorio → **Settings** → **Secrets and variables** → **Actions**.
2. Añade estos secretos:
   - `QMC_URL`
   - `QMC_USERNAME`
   - `QMC_PASSWORD`
   - `GROQ_API_KEY`

---

## 🚀 Actualizaciones Futuras

Cuando hagas cambios en el proyecto:

```bash
git add .
git commit -m "Descripción del cambio"
git push
```

---

## ⚠️ IMPORTANTE: Verificar antes de subir

Antes de hacer `git push`, SIEMPRE verifica que no estés subiendo credenciales:

```bash
git status
```

Si ves `.env` o `browser_state.json` listado, **NO HAGAS PUSH** y avísame.
