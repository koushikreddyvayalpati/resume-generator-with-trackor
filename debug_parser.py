#!/usr/bin/env python3
import json
from manual_resume_parser import parse_updated_content_to_resume

# Your exact input
user_input = """UPDATED TITLE
Software Engineer (Forward Deployed, Solutions Engineering, Data & AI Systems)

UPDATED SUMMARY
Software Engineer with 4+ years of experience designing and deploying end-to-end data and AI systems that transform unstructured data into structured, production-ready workflows. Experienced in working directly with customers and stakeholders to translate ambiguous requirements into scalable solutions, including document processing pipelines, API integrations, and cloud deployments. Strong focus on system reliability, performance optimization, and delivering real-world implementations that enable AI systems to operate effectively in production environments.

UPDATED SKILLS
Languages: Python, Java, JavaScript, TypeScript
Frontend: React.js, Angular, Redux, HTML, CSS
Backend: Node.js, Express.js, Spring Boot, FastAPI
APIs & Integration: REST APIs, Webhooks, API Integration, JSON
Data & Databases: SQL, PostgreSQL, MongoDB
Data & Streaming: Kafka, ETL Pipelines
Cloud & DevOps: AWS (S3, EC2), Docker, CI/CD
Systems: Microservices, Distributed Systems
Testing: JUnit, Jest, Integration Testing, API Testing
Tools: Postman, Git

MODIFIED EXPERIENCE SECTIONS

McKinsey & Company | CA, USA
Software Engineer (Applied AI, Data & Systems Engineering) | May 2025 – Present

● Designed and deployed end-to-end data pipelines to process unstructured data sources, transforming raw documents into structured formats and improving data usability by 40% for downstream AI workflows.
● Built document processing workflows using Python and API integrations to automate ingestion, transformation, and routing of unstructured data, improving processing efficiency by 35% across distributed systems.
● Worked directly with stakeholders to gather requirements and translate ambiguous business workflows into scalable system architectures, improving solution adoption and reducing iteration cycles across projects.
● Engineered backend orchestration layers using Node.js and FastAPI to support AI-driven workflows, enabling reliable execution of high-volume pipelines and improving throughput across production environments.
● Developed full-stack interfaces using React.js to enable internal users to monitor pipeline execution and manage workflows, improving visibility and reducing operational overhead across teams.
● Deployed solutions across AWS using Docker and CI/CD pipelines, ensuring scalable, reliable production systems and reducing deployment friction across environments.
● Led end-to-end deployment of data and AI systems, implementing testing, monitoring, and validation strategies that reduced deployment-related failures by 30% and improved system reliability.
● Troubleshot complex issues across pipelines, APIs, and integrations, identifying root causes and reducing system failure rates by 25% across critical workflows.

Uber | CA, USA
Full Stack Developer | February 2024 – May 2025

● Built real-time event-driven data pipelines using Kafka and Python microservices, processing over 75,000 daily events and enabling structured data flow across distributed systems for downstream applications.
● Developed backend services using Node.js supporting over 200,000 weekly transactions, ensuring high system reliability and consistent performance across large-scale production environments.
● Designed and integrated REST APIs to connect frontend applications built with React.js to backend services, improving data consistency by 20% and enabling seamless user interactions.
● Optimized system performance and reduced latency by 30% through efficient API design and query optimization, improving responsiveness across high-traffic applications.
● Collaborated with cross-functional teams to design and deploy scalable full-stack solutions aligned with operational and business requirements.

KPMG | India
Java Full Stack Developer | September 2021 – July 2022

● Developed backend systems using Spring Boot and SQL to process over 100,000+ records monthly, improving efficiency and reliability of enterprise data workflows across applications.
● Built frontend components using Angular and Redux to enable dynamic user interfaces, improving usability and data interaction across enterprise platforms.
● Designed REST APIs to enable integration between systems, reducing data retrieval time by 25% and improving system performance across business-critical workflows.
● Automated data processing workflows using Python and AWS services, reducing manual effort by 30% and improving consistency of operational processes across systems.

Trigent Software | India
Frontend Developer Intern | March 2021 – August 2021

● Developed responsive frontend applications using React.js, HTML, and CSS, enabling seamless interaction with backend APIs and improving usability across enterprise systems.
● Integrated frontend components with backend services using REST APIs, ensuring consistent data flow and improving reliability across application layers.
● Built unit and integration tests using Jest to identify defects and improve application stability across releases in production environments.
● Collaborated with cross-functional teams to deliver scalable UI components aligned with system requirements and business needs.
"""

# Load base resume
with open("/Users/tharun/resume-tool/config/base_resume.json") as f:
    base = json.load(f)

# Parse
result = parse_updated_content_to_resume(user_input, base)

# Show results
print("=" * 80)
print(f"TITLE: {result['title'][:50]}...")
print(f"\nEXPERIENCE ENTRIES PARSED: {len(result['experience'])}")
for i, exp in enumerate(result['experience']):
    print(f"\n  [{i+1}] {exp['company']} - {exp['title']}")
    print(f"      Location: {exp['location']}, Dates: {exp['dates']}")
    print(f"      Bullets: {len(exp['bullets'])}")

print(f"\nSKILLS: {len(result['technical_skills'])} categories")
print("=" * 80)
