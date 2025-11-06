# REST API Spec

```yaml
openapi: 3.0.0
info:
  title: "Contextiva Knowledge Engine API"
  version: "1.0.0"
  description: "REST API for the Contextiva Knowledge Engine, providing services for project management, document ingestion, and RAG retrieval for AI agents."
servers:
  - url: "/api/v1"
    description: "API v1"
  - url: "http://localhost:8000/api/v1"
    description: "Local Development Server"

security:
  - bearerAuth: []

paths:
  /auth/token:
    post:
      summary: "Login for Access Token"
      tags:
        - "Authentication"
      requestBody:
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: "object"
              properties:
                username:
                  type: "string"
                password:
                  type: "string"
      responses:
        "200":
          description: "Successful login"
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Token"

  /projects:
    get:
      summary: "List all projects"
      operationId: "list_projects_api_v1_projects_get"
      security:
        - bearerAuth: []
      tags:
        - "Projects"
      parameters:
        - name: "skip"
          in: "query"
          required: false
          schema:
            type: "integer"
            default: 0
        - name: "limit"
          in: "query"
          required: false
          schema:
            type: "integer"
            default: 100
      responses:
        "200":
          description: "A list of projects"
          content:
            application/json:
              schema:
                type: "array"
                items:
                  $ref: "#/components/schemas/ProjectResponse"
        "401":
          $ref: "#/components/responses/UnauthorizedError"

    post:
      summary: "Create a new project"
      operationId: "create_project_api_v1_projects_post"
      security:
        - bearerAuth: []
      tags:
        - "Projects"
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ProjectCreate"
      responses:
        "201":
          description: "Project created successfully"
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ProjectResponse"
        "401":
          $ref: "#/components/responses/UnauthorizedError"
        "422":
          $ref: "#/components/responses/ValidationError"

  /projects/{id}:
    get:
      summary: "Get a project by ID"
      operationId: "get_project_api_v1_projects__id__get"
      security:
        - bearerAuth: []
      tags:
        - "Projects"
      parameters:
        - name: "id"
          in: "path"
          required: true
          schema:
            type: "string"
            format: "uuid"
      responses:
        "200":
          description: "Project details"
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ProjectResponse"
        "401":
          $ref: "#/components/responses/UnauthorizedError"
        "404":
          $ref: "#/components/responses/NotFoundError"

components:
  securitySchemes:
    bearerAuth:
      type: "http"
      scheme: "bearer"
      bearerFormat: "JWT"

  schemas:
    ProjectBase:
      type: "object"
      properties:
        name:
          type: "string"
        description:
          type: "string"
          nullable: true
        tags:
          type: "array"
          items:
            type: "string"
          nullable: true
    
    ProjectCreate:
      allOf:
        - $ref: "#/components/schemas/ProjectBase"

    ProjectResponse:
      allOf:
        - $ref: "#/components/schemas/ProjectBase"
        - type: "object"
          properties:
            id:
              type: "string"
              format: "uuid"
            status:
              type: "string"
              example: "Active"
              
    Token:
      type: "object"
      properties:
        access_token:
          type: "string"
        token_type:
          type: "string"
          example: "bearer"

  responses:
    UnauthorizedError:
      description: "Authentication failed or token missing"
      content:
        application/json:
          schema:
            type: "object"
            properties:
              detail:
                type: "string"
                example: "Not authenticated"
                
    NotFoundError:
      description: "Resource not found"
      content:
        application/json:
          schema:
            type: "object"
            properties:
              detail:
                type: "string"
                example: "Project not found"

    ValidationError:
      description: "Input validation failed"
      content:
        application/json:
          schema:
            type: "object"
            properties:
              detail:
                type: "array"
                items:
                  type: "object"
                  properties:
                    loc:
                      type: "array"
                      items:
                        type: "string"
                    msg:
                      type: "string"
                    type:
                      type: "string"
```
