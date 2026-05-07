"""pockets.py — Source of truth for the 7 BID-IA thematic pockets.

All definitions here are derived from POCKETS_DELIMITACION.md, which is itself
based on the Fedesarrollo & BID deck (April 2026).
"""

POCKETS = {
    "evaluacion_experimental": {
        "label": "Evaluación Experimental",
        "line": "Adopción (Pocket 1)",
        "priority": "HIGH",
        "question": (
            "¿Qué determina los resultados de la adopción de IA en las firmas? "
            "¿Cuáles son los mecanismos que explican cuándo y por qué la IA funciona o no? "
            "¿Qué lecciones sirven para diseñar experimentos en LATAM?"
        ),
        "why": (
            "Base empírica para diseñar el experimento en Guatiguará (primer RCT adopción IA MiPyMEs LATAM). "
            "Documenta heterogeneidad de efectos según tipo de tarea y trabajador (novatos vs expertos). "
            "Identifica condiciones habilitantes: datos, calibración, diseño de interfaz."
        ),
        "anchor_papers": [
            "Brynjolfsson, Li & Raymond (2025) — Generative AI at Work — QJE — RCT call center +15%",
            "Dell'Acqua et al. (2023) — Navigating the Jagged Technological Frontier — HBS WP — RCT BCG",
            "Noy & Zhang (2023) — Experimental Evidence on AI Productivity — Science — RCT online workers",
            "Peng et al. (2023) — Impact of AI on Developer Productivity — Microsoft — RCT GitHub Copilot",
            "Caplin et al. (2024) — The ABCs of Who Benefits from Working with AI — Mgmt Sci — lab",
            "Otis et al. (2024) — The Uneven Impact of GenAI on Entrepreneurs — HBS WP — Sur Global RCT",
            "McElheran, Brynjolfsson et al. (2024) — AI Adoption in America — JEMS — descriptive diffusion",
        ],
        "queries": [
            "generative AI RCT randomized controlled trial productivity worker 2023-2026",
            "AI causal effect firm productivity quasi-experimental DiD identification",
            "generative AI task-level experiment treatment effect heterogeneous",
            "AI adoption impact mechanism worker skill level experience novice expert",
            "field experiment AI adoption SME developing country LATAM",
            "AI productivity causal inference instrumental variable call center knowledge worker",
            "staggered DiD AI adoption Sun Abraham estimator",
            "jagged frontier AI knowledge worker experiment quality output",
        ],
        "quality_signals": [
            "Diseño experimental explícito: RCT, DiD, IV, RDD, matching",
            "Heterogeneidad de efectos por habilidad, experiencia o tipo de tarea",
            "Contexto de workers o firmas reales (no solo laboratorio universitario)",
            "Métricas de productividad medibles: RPH, output quality, speed",
            "Contexto Sur Global, MiPyMEs o LATAM = bonus alto",
        ],
        "accept_criteria": [
            "Estudia IA/LLM/GenAI específicamente (no automation genérica pre-2020)",
            "Diseño experimental o cuasi-experimental (RCT, DiD, IV, matching)",
            "Mide productividad, output quality o eficiencia laboral directamente",
            "Nivel de análisis: tarea o trabajador (no solo agregado macroeconómico)",
            "Identificación causal explícita — no solo correlación descriptiva",
        ],
        "keywords": [
            "RCT", "randomized", "DiD", "difference-in-differences", "quasi-experimental",
            "instrumental variable", "treatment effect", "heterogeneous effects", "causal",
            "field experiment", "knowledge worker", "task-level", "productivity",
            "generative AI", "LLM", "copilot", "staggered adoption",
        ],
    },

    "human_machine_interaction": {
        "label": "Human-Machine Interaction",
        "line": "HMI (Pocket 2)",
        "priority": "HIGH",
        "question": (
            "¿Cuándo y por qué la interacción entre humanos e IA genera valor o lo destruye? "
            "¿Cuándo la combinación humano-IA supera al mejor de los dos por separado? "
            "¿Qué determina si el juicio humano complementa o degrada las predicciones de IA?"
        ),
        "why": (
            "La firma que adopta IA sin rediseñar procesos ni entrenar en uso puede destruir valor. "
            "La combinación humano-IA NO mejora por default. "
            "Explica dinámicas de confianza, calibración y dependencia. "
            "Clave para diseñar intervenciones: ¿qué training necesitan los trabajadores?"
        ),
        "anchor_papers": [
            "Vaccaro et al. (2024) — complementariedad realizada humano-IA",
            "Dietvorst et al. (2015) — algorithm aversion and appreciation",
            "Agarwal et al. (2023) — AI in clinical decision making",
            "Hemmer et al. (2023) — delegación dinámica humano-IA",
            "Dell'Acqua et al. (2023) — over-reliance fuera de la jagged frontier",
        ],
        "queries": [
            "human-AI complementarity collaboration productivity experiment 2023-2026",
            "algorithm aversion appreciation over-reliance AI trust calibration",
            "human AI teaming task delegation complementarity value creation",
            "AI decision support worker trust automation bias miscalibration",
            "human machine interaction productivity knowledge work real setting",
            "AI augmentation vs automation worker performance difference outcome",
            "AI literacy training worker adoption complementarity experiment",
            "algorithmic aversion over-reliance miscalibration task outcome skilled",
        ],
        "quality_signals": [
            "Mide interacción humano-IA explícitamente (no solo uso individual de IA)",
            "Identifica condiciones de complementariedad vs sustitución",
            "Estudia confianza, calibración, over-reliance o under-reliance",
            "Diseño experimental o cuasi-experimental",
            "Contexto de firmas o trabajos reales (no solo interfaces de laboratorio)",
        ],
        "accept_criteria": [
            "Estudia la interacción directa humano-IA (no solo adopción de herramienta)",
            "Analiza complementariedad, sobre-dependencia, o aversión al algoritmo",
            "Mide outcomes del equipo humano-IA vs. solo humano o solo IA",
            "Identifica mecanismo de confianza, calibración o delegación",
            "Relevante para decisiones en entornos laborales o firmas reales",
        ],
        "keywords": [
            "human-AI complementarity", "algorithm aversion", "over-reliance",
            "automation bias", "AI trust", "calibration", "human-AI teaming",
            "decision support", "augmentation", "delegation", "collaboration",
            "task allocation", "AI literacy", "expertise", "miscalibration",
        ],
    },

    "innovacion_difusion": {
        "label": "Innovación y Difusión",
        "line": "Innovación y Difusión (Pocket 3)",
        "priority": "MEDIUM",
        "question": (
            "¿Cómo se difunde la IA dentro de y entre firmas, y cuándo se traduce en ganancias medibles "
            "de productividad e innovación? ¿Por qué coexisten avances tecnológicos con estancamiento en "
            "productividad medida (productivity paradox)?"
        ),
        "why": (
            "Una firma puede adoptar IA sin ver cambios en productividad agregada (J-curve de Brynjolfsson). "
            "Los intangibles (datos, procesos, capital humano) son la diferencia entre capturar valor o no. "
            "Define timing de intervención política: ¿cuándo es demasiado pronto / tarde?"
        ),
        "anchor_papers": [
            "Brynjolfsson et al. (2019, 2021) — J-curve, paradoja de la productividad",
            "Acemoglu (2024) — límites de los efectos de IA en productividad agregada",
            "Comin & Mestieri (2018) — difusión tecnológica entre países",
            "McElheran, Brynjolfsson et al. (2024) — adopción IA en firmas americanas (descriptivo)",
            "Lo Turco & Sterlacchini (2024) — factores que mejoran adopción IA en firmas (panel)",
        ],
        "queries": [
            "AI diffusion firm-level productivity measurement paradox J-curve",
            "technology diffusion adoption patterns between firms spillovers productivity",
            "AI intangibles complementary investments organizational capital productivity gap",
            "generative AI firm adoption rate determinants barriers 2023-2026",
            "AI productivity paradox measurement lag organizational change firm",
            "technology adoption S-curve AI small medium firm barriers enablers",
            "AI innovation diffusion SME developing country LATAM productivity",
            "AI adoption complementarities data human capital process redesign firm",
        ],
        "quality_signals": [
            "Distingue exposición/piloto vs adopción integrada (profundidad, no solo presencia)",
            "Estudia inversiones complementarias necesarias para capturar valor",
            "Mide heterogeneidad de adopción por tamaño de firma, sector, capacidades",
            "Identifica brechas entre efecto task-level vs firm-level",
            "Panel o longitudinal que capture dinámica temporal de adopción",
        ],
        "accept_criteria": [
            "Estudia difusión o adopción de IA a nivel firma (no solo task-level)",
            "Analiza barreras o habilitadores de adopción y escala",
            "Identifica inversiones complementarias necesarias (datos, procesos, capital humano)",
            "Mide resultados de productividad o innovación a nivel firma",
            "Relevante para MiPyMEs o firmas en economías en desarrollo",
        ],
        "keywords": [
            "diffusion", "adoption rate", "S-curve", "J-curve", "productivity paradox",
            "complementary investment", "intangible capital", "organizational change",
            "firm heterogeneity", "technology spillover", "measurement lag",
            "digital transformation", "AI maturity", "scale", "pilot to production",
        ],
    },

    "labor": {
        "label": "Labor y Mercado de Trabajo",
        "line": "Labor y Mercado de Trabajo (Pocket 4)",
        "priority": "HIGH",
        "question": (
            "¿Cómo afecta la adopción de IA a la distribución del trabajo y valor dentro de firmas? "
            "¿Cómo cambian salarios entre trabajadores con distinto nivel de habilidad? "
            "¿Qué implica para el diseño de intervenciones en MiPyMEs LATAM?"
        ),
        "why": (
            "La decisión de qué automatizar no es solo técnica: redistribuye valor entre trabajadores. "
            "Una firma que automatiza sin diseño deliberado puede perder capital humano crítico. "
            "Evidencia crítica para policy makers BID: ¿cuándo intervenir y cómo proteger a workers?"
        ),
        "anchor_papers": [
            "Acemoglu & Restrepo (2022) — tareas rutinizables vs no-rutinizables, automatización",
            "Autor (2024) — síntesis efectos IA en trabajo y salarios",
            "Humlum & Vestergaard (2025) — efectos salariales, redistribución dentro de firmas",
            "Acemoglu & Restrepo (2018, 2019) — Task-Based framework",
        ],
        "queries": [
            "AI impact labor wages within-firm distribution skilled unskilled 2023-2026",
            "task automation AI employment effects worker reallocation occupation",
            "generative AI wage inequality skill premium polarization earnings",
            "AI automation task-based model routine non-routine occupations Acemoglu",
            "AI worker retraining reskilling effectiveness firm labor market",
            "AI employment creation destruction net effect occupation-level",
            "AI labor market effects developing countries LATAM Colombia informal",
            "within-firm AI adoption redistribution value roles tasks Humlum",
        ],
        "quality_signals": [
            "Mide efectos heterogéneos por nivel de habilidad, ocupación o tarea",
            "Distingue efectos dentro de firma vs entre firmas (within vs between)",
            "Tiene datos de salarios o empleo reales (no solo self-report)",
            "Identifica mecanismo: task displacement, capital-skill complementarity, wage bargaining",
            "Contexto LatAm o Sur Global = bonus alto",
        ],
        "accept_criteria": [
            "Analiza efectos de IA en empleo, salarios o composición de tareas",
            "Nivel micro: trabajador, ocupación o firma (no solo macroeconómico)",
            "Distingue entre tipos de trabajadores (skill level, experiencia, ocupación)",
            "Identifica mecanismo de redistribución (no solo correlación agregada)",
            "Período relevante: IA generativa post-2020, preferiblemente 2022-2026",
        ],
        "keywords": [
            "task automation", "employment displacement", "wage effects", "skill premium",
            "labor demand", "occupation", "routine tasks", "non-routine", "reskilling",
            "worker reallocation", "within-firm redistribution", "labor market",
            "human capital", "capital-skill complementarity", "wage inequality",
        ],
    },

    "desigualdad": {
        "label": "Desigualdad",
        "line": "Desigualdades (Pocket 5)",
        "priority": "HIGH",
        "question": (
            "¿Bajo qué condiciones estructurales la adopción de IA amplía o reduce brechas existentes? "
            "¿Qué intervenciones pueden corregir asimetrías según habilidad, tamaño de firma, "
            "geografía y género?"
        ),
        "why": (
            "Un efecto promedio positivo puede ocultar que solo los trabajadores más calificados se benefician. "
            "LATAM ya tiene alta desigualdad; IA puede amplificarla sin políticas activas. "
            "99.5% de firmas LATAM son MiPyMEs: el acceso diferencial a IA define el mapa competitivo."
        ),
        "anchor_papers": [
            "Autor et al. (2020) — fall of the middle class, polarización labor",
            "Andrews et al. (2016) — frontier vs laggard firms, divergencia productividad",
            "Akerman et al. (2015) — broadband, complementariedad skilled workers",
            "Babina et al. (2023) — AI y desigualdad salarial entre firmas",
        ],
        "queries": [
            "AI inequality heterogeneous effects skill size firm geography 2023-2026",
            "generative AI benefits distribution high low skill workers experiment",
            "AI adoption frontier firms laggard firms divergence productivity gap",
            "AI gender gap women workers benefits adoption outcomes",
            "digital divide AI access SME large firm LATAM developing country",
            "AI wage inequality income distribution polarization gig economy workers",
            "technology adoption heterogeneous effects firm size sector productivity gap",
            "AI complementarity skilled workers inequality amplification Babina Autor",
        ],
        "quality_signals": [
            "Estudia heterogeneidad de efectos explícitamente (no solo average treatment effect)",
            "Desglosa por habilidad, género, tamaño de firma o geografía",
            "Conecta acceso diferencial con resultados de productividad o salario",
            "Evidencia sobre frontrunners vs laggards en adopción IA",
            "Contexto LatAm, género, SME o economías en desarrollo = bonus alto",
        ],
        "accept_criteria": [
            "Analiza efectos heterogéneos de IA según tamaño, skill, género o acceso",
            "Compara firmas adoptantes vs no-adoptantes o trabajadores de diferente perfil",
            "Mide efectos distributivos explícitamente (no solo promedio agregado)",
            "Identifica condiciones que amplifican o reducen brechas existentes",
            "Relevante para contexto LATAM o economías en desarrollo (bonus)",
        ],
        "keywords": [
            "inequality", "heterogeneous effects", "skill premium", "digital divide",
            "frontier firms", "laggard firms", "gender gap", "SME large firm",
            "geographic disparities", "polarization", "income distribution",
            "distributional effects", "technology gap", "access to AI",
        ],
    },

    "management": {
        "label": "Management y Organización",
        "line": "Gestión y Organización (Pocket 6)",
        "priority": "HIGH",
        "question": (
            "¿Cómo la organización interna y las estructuras de decisión determinan adopción y captura "
            "de valor de la IA? ¿Qué roles, competencias y procesos habilitan implementación exitosa? "
            "¿Por qué el 70% de pilotos no escalan a producción?"
        ),
        "why": (
            "Firmas con tecnología idéntica capturan valor diferente según su diseño organizacional. "
            "La mayoría de pilotos falla por falta de capacidades organizacionales, no de tecnología. "
            "Define qué tiene que cambiar adentro de la firma para que la inversión en IA se traduzca en valor."
        ),
        "anchor_papers": [
            "Brynjolfsson & McAfee (2014) — complementariedades organizacionales con IA",
            "McElheran et al. (2024) — AI Adoption in America, decisiones de firma",
            "Acemoglu et al. (2023) — cambio organizacional e IA",
            "Hansen et al. (2024) — definición operacional de adopción integrada",
            "MIT CISR (2025) — piloto a producción, tasa de abandono 70%",
        ],
        "queries": [
            "AI organizational adoption management capabilities firm 2023-2026",
            "generative AI implementation failure success factors organizational change",
            "AI complementary investments human capital process redesign firm value",
            "AI adoption decision-maker leadership CEO strategy firm performance",
            "digital transformation AI integration SME barriers enablers pilot scale",
            "AI governance internal firm algorithmic transparency decision making",
            "AI management practices productivity organizational capital Brynjolfsson",
            "AI change management talent upskilling firm readiness pilot production",
        ],
        "quality_signals": [
            "Estudia factores organizacionales que determinan éxito/fracaso de adopción",
            "Mide complementariedades: IA + training, IA + reorganización de procesos",
            "Distingue firmas que capturan valor vs no (no solo que adoptaron)",
            "Evidencia sobre MiPyMEs o firmas con recursos limitados = bonus",
            "Marco de gobernanza interna con aplicabilidad práctica",
        ],
        "accept_criteria": [
            "Estudia organización interna, gestión o capacidades de la firma",
            "Vincula prácticas de gestión con adopción exitosa o resultados de IA",
            "Analiza inversiones complementarias (reentrenamiento, rediseño de procesos)",
            "Identifica qué tipo de firma o gerente logra capturar valor de la IA",
            "Evidencia empírica rigurosa (no solo framework teórico sin datos)",
        ],
        "keywords": [
            "organizational capabilities", "change management", "implementation",
            "complementary investments", "process redesign", "AI governance",
            "management practices", "organizational capital", "firm readiness",
            "digital transformation", "talent", "upskilling", "pilot to production",
            "AI strategy", "leadership", "organizational change",
        ],
    },

    "policy": {
        "label": "Policy y Gobernanza",
        "line": "Ética, Gobernanza y Política Regulatoria (Pockets 7+8)",
        "priority": "MEDIUM",
        "question": (
            "¿Cómo marcos regulatorios y políticas públicas inciden en la toma de decisiones de adopción? "
            "¿Qué combinaciones de políticas aceleran o frenan adopción? "
            "¿Cómo diseñar política que maximice valor sin amplificar desigualdad? "
            "¿Qué estructuras de gobernanza interna desarrollan las firmas para gestionar riesgos algorítmicos?"
        ),
        "why": (
            "Regulación, incentivos fiscales y estándares de datos definen el entorno de decisión de la firma. "
            "BID es institución de desarrollo → las recomendaciones tienen que ser accionables en LatAm. "
            "La ética y gobernanza interna son parte de la decisión de adopción, no un añadido posterior."
        ),
        "anchor_papers": [
            "GDPR (2018), LGPD Brasil (2020), EU AI Act (2024) — marcos normativos",
            "OECD (2024, 2025) — adopción IA MiPyMEs, marcos regulatorios",
            "McKinsey & WEF (2026) — barreras sistémicas a adopción",
            "Policy briefs BID — recomendaciones para miembros",
        ],
        "queries": [
            "AI regulation policy adoption SME firm impact causal 2023-2026",
            "EU AI Act GDPR firm adoption compliance cost benefit empirical",
            "AI public policy intervention adoption developing countries LATAM Colombia",
            "AI algorithmic governance transparency explainability firm decision making",
            "AI ethics governance organizational risk management internal firm",
            "AI regulation uncertainty compliance cost SME developing country effect",
            "public policy AI diffusion SME support programs evidence evaluation",
            "AI governance framework accountability algorithmic bias organizational firm",
        ],
        "quality_signals": [
            "Estudia efecto causal o cuasi-causal de política/regulación en adopción",
            "Evidencia empírica (no solo normativa) sobre impacto regulatorio",
            "Contexto LatAm o economías en desarrollo = bonus alto",
            "Distingue efectos por tipo de firma (MiPyME vs grande)",
            "Marco de gobernanza interna con aplicabilidad práctica",
        ],
        "accept_criteria": [
            "Analiza política pública, regulación o gobernanza de IA con enfoque en firmas",
            "Vincula marco regulatorio con decisiones de adopción o innovación",
            "Mide efectos de política en comportamiento de firmas o trabajadores",
            "Relevante para economías en desarrollo o LATAM (preferiblemente)",
            "Evidencia empírica o análisis de caso riguroso (no solo descripción normativa)",
        ],
        "keywords": [
            "AI regulation", "governance", "EU AI Act", "GDPR", "LGPD",
            "policy framework", "compliance", "transparency", "explainability",
            "algorithmic accountability", "AI ethics", "public policy",
            "regulatory uncertainty", "digital policy", "SME policy",
            "incentives", "data governance",
        ],
    },
}

RUBRIC = """
RÚBRICA DE EVALUACIÓN (escala 0-11):

| Criterio       | Escala | Descripción                                                                 |
|----------------|--------|-----------------------------------------------------------------------------|
| Metodología    | 0-4    | 4=RCT/cuasi-exp, 3=panel/FE, 2=framework/mixed, 1=descriptivo, 0=teoría    |
| Causalidad     | 0-2    | 2=IV/RCT/DiD explícito, 1=correlación fuerte con controles, 0=sin evidencia |
| Top-tier       | 0-2    | 2=venue top o autores referentes, 1=arXiv/WP sólido, 0=desconocido         |
| Novedad        | -1/0/1 | 1=2022-2026, 0=2020-2021, -1=pre-2020 (pre-GenAI era)                      |
| Relevancia     | 0-2    | 2=responde pregunta central del pocket, 1=contexto útil, 0=no relevante     |

UMBRALES DE DECISIÓN:
- ACEPTADO : score ≥ 7
            OR (score ≥ 5 AND relevancia=2 AND ≥3 criterios del pocket cumplidos)
- REVISAR  : score 3-6 (o score ≥ 5 sin cumplir condición anterior)
- RECHAZADO: score < 3 OR relevancia = 0 (sin importar metodología)

REGLA CRÍTICA: un paper con metodología=4 pero relevancia=0 es RECHAZADO.
La relevancia al pocket no es opcional.
"""

PROJECT_CONTEXT = """
PROYECTO: BID-IA — Adopción de IA en Firmas en Colombia y LATAM
INSTITUCIÓN: Fedesarrollo & Banco Interamericano de Desarrollo (BID)
OBJETIVO: Identificar qué determina si una firma adopta IA efectivamente y captura valor.
          ¿Qué condiciones habilitantes requieren las MiPyMEs de LATAM?
LENTE MICRO: Toda la revisión se organiza desde la decisión de la firma individual.
             Macro y policy son contexto, no el foco principal.
EXPERIMENTO PROPIO: Guatiguará — primer RCT de adopción IA en MiPyMEs de LATAM.
                    La literatura debe informar el diseño de este experimento.
META: 420 papers (60 por pocket), ≥50 ACEPTADOS en total.
"""