from pydantic import BaseModel, Field

class postcreate(BaseModel):
    title: str = Field(..., example="My Post Title")
    content: str = Field(..., example="This is the content of my post.")
    published: bool = Field(default=True, example=True)