"""Static example estimations injected into the LLM context (CAG). Are the knowledge base of the LLM."""

ESTIMATION_EXAMPLES = [
    {
        "meeting_summary": "El cliente necesita una plataforma web de gestión de inventario...",
        "estimation": """
        ## Estimación: Plataforma de Gestión de Inventario
        
        ### Desglose de tareas:
        1. Diseño UI/UX: 40 horas
        2. Backend API (CRUD inventario): 60 horas
        3. Autenticación y roles: 20 horas
        4. Dashboard con métricas: 30 horas
        5. Testing y QA: 25 horas
        
        **Total estimado: 175 horas**
        **Equipo recomendado: 2 desarrolladores full-stack + 1 diseñador UX (part-time)**
        **Duración estimada: 6-8 semanas**
        """
    },
    {
        "meeting_summary": "El cliente necesita una plataforma web de servicios de contabilidad...",
        "estimation": """
        ## Estimación: Plataforma de Servicios de Contabilidad
        
        ### Desglose de tareas:
        1. Diseño UI/UX: 20 horas
        2. Backend API (CRUD contabilidad): 40 horas
        3. Autenticación y roles: 10 horas
        4. Dashboard con métricas: 15 horas
        5. Testing y QA: 15 horas
        """
    }
]
