```mermaid
graph TD
    subgraph "Actors & Devices"
        A[Student with RFID Card]
        B[Staff Member]
        C[Administrator]
        D["RFID Clearance Device - (ESP32)"]
        E[Admin's Computer - (Web Browser)]
        F[Staff Computer -(Web Browser)]
    end

    subgraph "Frontend (Streamlit)"
        G[Student Portal]
        H[Staff Portal]
        I[Admin Portal]
        J[Device Management]
    end

    subgraph "Backend API (FastAPI)"
        K[Authentication Router <br/>(/token, /users)]
        L[Student Router <br/>(/students)]
        M[Clearance Router <br/>(/clearance)]
        N[Device Router <br/>(/devices)]
        O[RFID Router <br/>(/rfid)]
        P[Admin Router <br/>(/admin)]
    end

    subgraph "Business Logic Layer"
        Q[User Management CRUD]
        R[Student Management CRUD]
        S[Clearance Management CRUD]
        T[Device Management CRUD]
        U[RFID Processing CRUD]
    end

    subgraph "Database Models (SQLModel)"
        V[User Model <br/>(Staff/Admin)]
        W[Student Model]
        X[Clearance Model]
        Y[Device Model]
        Z[Department Enum]
    end

    subgraph "Database"
        AA[(PostgreSQL DB <br/>Supabase)]
    end

    %% --- Workflow 1: Student Checks Clearance Status ---
    subgraph "Workflow 1: Student Self-Check"
        A -- 1. Taps RFID Card --> D
        D -- 2. Sends tag_id via API --> O
        O -- 3. Validates device API key --> U
        U -- 4. Queries student by tag_id --> R
        R -- 5. Gets student data --> W
        W -- 6. Queries database --> AA
        AA -- 7. Returns student + clearance --> R
        R -- 8. Formats response --> O
        O -- 9. Returns JSON to device --> D
        D -- 10. Displays clearance status --> A
    end

    %% --- Workflow 2: Staff Updates Clearance ---
    subgraph "Workflow 2: Staff Clearance Update"
        B -- 1. Logs into staff portal --> H
        H -- 2. Authenticates via JWT --> K
        K -- 3. Validates staff credentials --> Q
        B -- 4. Scans student card/enters ID --> H
        H -- 5. Sends clearance update --> M
        M -- 6. Validates department permission --> S
        S -- 7. Updates clearance record --> X
        X -- 8. Writes to database --> AA
        AA -- 9. Confirms update --> S
        S -- 10. Returns success --> M
        M -- 11. Notifies staff portal --> H
        H -- 12. Shows confirmation --> B
    end

    %% --- Workflow 3: Admin Management ---
    subgraph "Workflow 3: Admin Operations"
        C -- 1. Logs into admin portal --> I
        I -- 2. Authenticates as admin --> K
        K -- 3. Validates admin role --> Q
        C -- 4. Manages users/students/devices --> I
        I -- 5. Routes to appropriate endpoint --> P
        P -- 6. Performs CRUD operations --> Q
        P -- 6b. Student operations --> R
        P -- 6c. Device operations --> T
        Q -- 7. Updates models --> V
        R -- 7b. Updates models --> W
        T -- 7c. Updates models --> Y
        V --> AA
        W --> AA
        Y --> AA
        AA -- 8. Confirms changes --> P
        P -- 9. Returns results --> I
        I -- 10. Updates admin interface --> C
    end

    %% --- Workflow 4: Device Registration & Linking ---
    subgraph "Workflow 4: Device & Tag Management"
        C -- 1. Registers new device --> I
        I -- 2. Calls device registration --> N
        N -- 3. Creates device record --> T
        T -- 4. Stores device info --> Y
        Y -- 5. Saves to database --> AA
        
        C -- 6. Prepares tag linking --> I
        I -- 7. Calls tag preparation --> P
        P -- 8. Links tag to student/staff --> U
        U -- 9. Updates tag associations --> AA
        
        D -- 10. Submits scanned tag --> N
        N -- 11. Processes tag submission --> T
        T -- 12. Validates and links --> Y
        Y -- 13. Confirms link --> AA
    end

    %% Styling
    style A fill:#FFE6E6,stroke:#333,stroke-width:2px
    style B fill:#E6F3FF,stroke:#333,stroke-width:2px
    style C fill:#E6FFE6,stroke:#333,stroke-width:2px
    style D fill:#D6EAF8,stroke:#333,stroke-width:2px
    style G fill:#FFF0E6,stroke:#333,stroke-width:2px
    style H fill:#E6F0FF,stroke:#333,stroke-width:2px
    style I fill:#F0FFE6,stroke:#333,stroke-width:2px
    style AA fill:#FFE6F0,stroke:#333,stroke-width:3px
```
