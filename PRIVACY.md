# Privacy & Compliance Framework

As a legal technology solution designed for South African legal practitioners, LexFlow is architected with data privacy, client confidentiality, and regulatory compliance as core principles. 

This document outlines the data handling architecture of LexFlow and its alignment with the Protection of Personal Information Act (POPIA) and principles of data sovereignty.

## 1. Data Residency & Sovereignty

LexFlow is designed as a locally-hosted backend service. When deployed on your firm's infrastructure or a localized server environment (e.g., an on-premise server or a local cloud region):

*   **Local Data Storage:** All extracted billing data, including client names and matter descriptions, are written to a local `billing.csv` file residing exclusively on the host machine. LexFlow does not utilize a centralized, multi-tenant cloud database.
*   **Ephemeral Audio Processing:** Audio files uploaded for transcription are written to a temporary directory (`tempfile`) and are securely deleted from the local disk immediately upon completion of the transcription and extraction process.

## 2. POPIA Compliance Alignment

LexFlow provides the technical infrastructure necessary for attorneys to maintain POPIA compliance, specifically addressing key conditions for lawful processing:

*   **Condition 3: Purpose Specification:** Data is processed strictly for the administrative purpose of accurate time tracking and billing generation.
*   **Condition 4: Further Processing Limitation:** Data processed through LexFlow remains under the exclusive control of the hosting firm. The LexFlow application does not subject the data to secondary processing, analytics, or monetization.
*   **Condition 7: Security Safeguards:** Through self-hosting, law firms retain complete operational control over the security perimeter protecting the underlying data (the `billing.csv` file and host server).

## 3. Third-Party Data Processing (Google Gemini API)

LexFlow utilizes the Google Gemini API (`gemini-2.5-flash`) for natural language processing of voice notes. Firm administrators must ensure that the integration of third-party Large Language Model (LLM) providers aligns with their firm-wide privacy policies and client mandates.

Important compliance considerations regarding the Google API integration:
*   **LLM Training Data:** As governed by Google Cloud's enterprise terms of service, data submitted to the paid Google Gemini Enterprise API is not used to train Google's foundational models.
*   **Encryption in Transit:** Audio data and extraction prompts are encrypted in transit (using TLS) when transmitted to Google's inference servers.
*   **Ephemeral Inference:** Administrators must verify that they are operating under the appropriate Google Cloud agreements which guarantee that data submitted for inference is processed ephemerally and is not persisted outside of the firm's administrative control.

*Note: Deployments utilizing the free tier of Google AI Studio are subject to different data policies. Practitioners must review Google's specific terms regarding data usage for free-tier services, as they may differ from commercial enterprise agreements.*

## 4. Operational Recommendations for Legal Practitioners

To maintain strict compliance and uphold client confidentiality while leveraging LexFlow, we recommend implementing the following operational safeguards:

1.  **Data Minimization (Anonymization):** When dictating voice notes, practitioners should refer to clients using file reference numbers or initials (e.g., "Matter 4052, client J.S.") rather than full names, thereby minimizing the transmission of Personally Identifiable Information (PII) to external APIs.
2.  **Infrastructure Security:** Deploy the FastAPI application within a secure, private network (VPN) or implement robust zero-trust authentication protocols (e.g., OAuth2, JWT) prior to exposing the endpoint.
3.  **Data Lifecycle Management:** Implement automated scheduling to rotate, securely archive, or purge the `billing.csv` file in strict accordance with your firm's mandated data retention and destruction policies.
4.  **Client Disclosures:** Ensure that standard client letters of engagement include comprehensive provisions regarding the firm's utilization of localized and cloud-based AI infrastructure for administrative and document processing workflows.

---
*Disclaimer: This document provides an architectural overview of data handling within the LexFlow application. It does not constitute formal legal advice. Law firms should consult with their internal risk and compliance officers to ensure their specific deployment strategy adheres to all regulatory and professional requirements.*
