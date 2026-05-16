# Changelog

## [2026-05-01] - Initial Project Setup and Repository Preparation

### Added
- [Gabriel S. Concepcion] Cloned and initialized the existing Pojangmacha project repository from Software Engineering 1 for cloud deployment preparation.
- [Gabriel S. Concepcion] Configured the local development environment and verified Python package dependencies.
- [Gabriel S. Concepcion] Organized the project structure and prepared documentation folders for deployment, architecture, and audit reports.
- [Gabriel S. Concepcion] Created the initial GitHub repository configuration for collaborative development and version control.

### Changed
- [Gabriel S. Concepcion] Updated application configuration files to support Azure App Service deployment.
- [Gabriel S. Concepcion] Modified environment variable handling to separate sensitive credentials from source code.

### Fixed
- [Gabriel S. Concepcion] Fixed missing dependency issues encountered during the first local project execution.
- [Gabriel S. Concepcion] Corrected repository folder paths and startup configuration for Linux-based deployment compatibility.

### Removed
- [Gabriel S. Concepcion] Removed unused temporary files and deprecated test assets inherited from the Software Engineering 1 version.

---

## [2026-05-03] - Database and Storage Integration

### Added
- [Gabriel S. Concepcion] Created Azure SQL Database for food menu data storage
- [Gabriel S. Concepcion] Created Azure Storage Account and Blob Container for food image uploads
- [Gabriel S. Concepcion] Added database connection logic using environment variables
- [Gabriel S. Concepcion] Implemented image upload functionality to Azure Blob Storage

### Changed
- [Gabriel S. Concepcion] Updated food management module to save image URLs in Azure SQL Database
- [Gabriel S. Concepcion] Modified storage configuration to use secure Azure connection string

### Fixed
- [Gabriel S. Concepcion] Fixed SQL connection timeout issue by updating firewall settings
- [Gabriel S. Concepcion] Fixed blob upload naming conflict using UUID-based filenames

---

## [2026-05-05] - Azure Deployment Preparation

### Added
- [Gabriel S. Concepcion] Created Azure Resource Group for centralized resource management
- [Gabriel S. Concepcion] Created Azure App Service Plan for hosting the web application
- [Gabriel S. Concepcion] Created Azure App Service Web App deployment target
- [Gabriel S. Concepcion] Added GitHub Actions workflow for automatic deployment to Azure

### Changed
- [Gabriel S. Concepcion] Updated application startup configuration for Azure App Service compatibility
- [Gabriel S. Concepcion] Modified environment variable handling using Azure App Settings

### Fixed
- [Gabriel S. Concepcion] Fixed deployment conflict issue in GitHub Actions OneDeploy workflow
- [Gabriel S. Concepcion] Fixed Git push rejection by synchronizing remote and local repository history

### Removed
- [Gabriel S. Concepcion] Removed unused local test deployment configuration files

---

## [2026-05-08] - Cloud Optimization and Security Configuration

### Added
- [Gabriel S. Concepcion] Configured Azure Application Insights for monitoring and diagnostics
- [Gabriel S. Concepcion] Added App Service environment variables for secure configuration management
- [Gabriel S. Concepcion] Enabled HTTPS-only traffic for Azure App Service security
- [Gabriel S. Concepcion] Configured Azure Blob Storage public access settings for food image hosting

### Changed
- [Gabriel S. Concepcion] Updated App Service startup configuration to use dynamic Azure-assigned PORT values
- [Gabriel S. Concepcion] Improved application deployment workflow with automated GitHub Actions triggers

### Fixed
- [Gabriel S. Concepcion] Fixed Azure App Service startup failure caused by incorrect Flet configuration
- [Gabriel S. Concepcion] Fixed image rendering issue caused by incorrect blob image URLs

### Removed
- [Gabriel S. Concepcion] Removed hardcoded localhost configuration from production deployment

---

## [2026-05-10] - Application Feature Improvements

### Added
- [Gabriel S. Concepcion] Added admin dashboard for managing food items
- [Gabriel S. Concepcion] Added CRUD operations for food records in Azure SQL Database
- [Gabriel S. Concepcion] Added image preview support for uploaded food images
- [Gabriel S. Concepcion] Added responsive UI adjustments for browser-based deployment

### Changed
- [Gabriel S. Concepcion] Updated Flet application to use WEB_BROWSER view for Azure compatibility
- [Gabriel S. Concepcion] Improved modal dialog workflow for Add Food and Edit Food actions

### Fixed
- [Gabriel S. Concepcion] Fixed issue where admin login failed after Azure deployment
- [Gabriel S. Concepcion] Fixed issue preventing uploaded food images from displaying in production environment
- [Gabriel S. Concepcion] Fixed App Service loading issue caused by incomplete startup configuration

---

## [2026-05-12] - Documentation and Architecture Finalization

### Added
- [Ma. Francheska R. Recierdo] Created Azure architecture diagram showing App Service, Azure SQL Database, and Blob Storage integration
- [Ma. Francheska R. Recierdo] Created deployment documentation with Azure Portal screenshots
- [Ma. Francheska R. Recierdo] Added cost estimation report using Azure Pricing Calculator
- [Ma. Francheska R. Recierdo] Prepared presentation slides and live demo walkthrough

### Changed
- [Ma. Francheska R. Recierdo] Updated architecture diagram to include security boundary and public/private access indicators
- [Ma. Francheska R. Recierdo] Refined cost optimization explanation using Azure free-tier and scaling strategies

### Fixed
- [Ma. Francheska R. Recierdo] Corrected architecture documentation labels for Azure Storage networking flow
- [Ma. Francheska R. Recierdo] Fixed inconsistent screenshot ordering in deployment documentation

---

## [2026-05-14] - Final Testing and Deployment Validation

### Added
- [Gabriel S. Concepcion] Conducted final cloud deployment validation on Azure App Service
- [Gabriel S. Concepcion] Verified GitHub Actions CI/CD deployment workflow functionality
- [Gabriel S. Concepcion] Added final production environment variable validation
- [Gabriel S. Concepcion] Completed end-to-end application testing for login, food management, and image storage

### Changed
- [Gabriel S. Concepcion] Updated deployment process documentation for final submission
- [Gabriel S. Concepcion] Improved presentation script for architecture and cost explanation sections

### Fixed
- [Gabriel S. Concepcion] Fixed Azure App Service deployment synchronization issue
- [Gabriel S. Concepcion] Fixed Add Food modal issue after browser deployment migration
- [Gabriel S. Concepcion] Fixed image upload access issue in Azure Blob Storage container

### Removed
- [Gabriel S. Concepcion] Removed unused debugging logs from production deployment