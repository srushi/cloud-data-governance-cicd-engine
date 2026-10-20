"""Cloud Data Governance & CI/CD Pipeline Engine.

Audits cloud data warehouse schemas (Snowflake / BigQuery, or local CSV
fixtures), detects data-quality exceptions, classifies them by type and
severity, and writes structured exception logs and summary reports.
"""

__version__ = "1.0.0"
