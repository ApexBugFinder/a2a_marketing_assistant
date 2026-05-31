import os
import time
import urllib.parse
import httpx
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from dotenv import load_dotenv
from typing import Optional
from models.linkedin_posts import LinkedInPost, LinkedInPostMetadata
from common.types import DeliverableStatus

load_dotenv()


class LinkedInPostArgs(BaseModel):
     author_urn: str = Field(description="LinkedIn author URN (e.g. 'urn:li:person:xxx' or 'urn:li:organization:xxx').")
     text: str = Field(description="The text content of the LinkedIn post.")
     hashtags: list[str] = Field(default_factory=list, description="List of hashtags to append to the post (without the # symbol).")
     image_url: Optional[str] = Field(default=None, description="Public URL of an image to attach to the post.")


class LinkedInRemovePostArgs(BaseModel):
     linkedin_post_id: str = Field(description="The LinkedIn post ID (URN) to delete, e.g. 'urn:li:share:xxx' or 'urn:li:ugcPost:xxx'.")


class LinkedInEditPostArgs(BaseModel):
     linkedin_post_id: str = Field(description="The LinkedIn post URN to edit, e.g. 'urn:li:ugcPost:xxx'.")
     text: str = Field(description="The updated text content of the post.")
     hashtags: list[str] = Field(default_factory=list, description="Updated list of hashtags to append (without the # symbol).")


class LinkedInPosterTools:
     def __init__(self):
          self.client_id = os.getenv("LINKEDIN_CLIENT_ID")
          self.client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
          self.access_token = None
          self.post_to_linkedin_tool = StructuredTool.from_function(
               coroutine=self.post_to_linkedin,
               name="LinkedIn Post Tool",
               description="Posts content to a LinkedIn account. Supports text, hashtags, and an optional image.",
               args_schema=LinkedInPostArgs,
               response_format="content",
          )
          self.remove_linkedin_post_tool = StructuredTool.from_function(
               coroutine=self.remove_linkedin_post,
               name="LinkedIn Remove Post Tool",
               description="Deletes a previously published LinkedIn post by its post ID.",
               args_schema=LinkedInRemovePostArgs,
               response_format="content",
          )
          self.edit_linkedin_post_tool = StructuredTool.from_function(
               coroutine=self.edit_linkedin_post,
               name="LinkedIn Edit Post Tool",
               description="Edits the text content and hashtags of an existing LinkedIn post.",
               args_schema=LinkedInEditPostArgs,
               response_format="content",
          )

     def _auth_headers(self) -> dict:
          return {
               "Authorization": f"Bearer {self.access_token}",
               "X-Restli-Protocol-Version": "2.0.0",
               "Content-Type": "application/json",
          }

     async def get_token(self):
          async with httpx.AsyncClient() as client:
               response = await client.post(
                    "https://www.linkedin.com/oauth/v2/accessToken",
                    data={
                         "grant_type": "client_credentials",
                         "client_id": self.client_id,
                         "client_secret": self.client_secret,
                    },
               )
          if response.status_code == 200:
               self.access_token = response.json().get("access_token")
          else:
               raise Exception(f"Failed to get access token: {response.text}")

     async def _upload_image(self, author_urn: str, image_url: str) -> str:
          """Downloads an image from image_url, uploads it to LinkedIn, and returns the asset URN."""
          async with httpx.AsyncClient() as client:
               # Step 1: register upload
               register_response = await client.post(
                    "https://api.linkedin.com/v2/assets?action=registerUpload",
                    json={
                         "registerUploadRequest": {
                         "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                         "owner": author_urn,
                         "serviceRelationships": [{
                              "relationshipType": "OWNER",
                              "identifier": "urn:li:userGeneratedContent",
                         }],
                         }
                    },
                    headers=self._auth_headers(),
               )
               register_response.raise_for_status()
               register_data = register_response.json()
               upload_url = (
                    register_data["value"]["uploadMechanism"]
                    ["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]
                    ["uploadUrl"]
               )
               asset_urn = register_data["value"]["asset"]

               # Step 2: download the image
               image_response = await client.get(image_url)
               image_response.raise_for_status()

               # Step 3: upload binary to LinkedIn
               await client.put(
                    upload_url,
                    content=image_response.content,
                    headers={"Authorization": f"Bearer {self.access_token}"},
               )

          return asset_urn

     async def post_to_linkedin(
          self,
          author_urn: str,
          text: str,
          hashtags: list[str] = [],
          image_url: Optional[str] = None,
     ) -> dict:
          """Posts a text update to LinkedIn, optionally with hashtags and an image."""
          if not self.access_token:
               await self.get_token()

          # Append hashtags to text
          if hashtags:
               tag_string = " ".join(f"#{tag}" for tag in hashtags)
               text = f"{text}\n\n{tag_string}"

          # Build media section if an image was provided
          if image_url:
               asset_urn = await self._upload_image(author_urn, image_url)
               share_media_category = "IMAGE"
               media = [{
                    "status": "READY",
                    "media": asset_urn,
               }]
          else:
               share_media_category = "NONE"
               media = []

          payload = {
               "author": author_urn,
               "lifecycleState": "PUBLISHED",
               "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                         "shareCommentary": {"text": text},
                         "shareMediaCategory": share_media_category,
                         **({"media": media} if media else {}),
                    }
               },
               "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
               },
          }

          async with httpx.AsyncClient() as client:
               response = await client.post(
                    "https://api.linkedin.com/v2/ugcPosts",
                    json=payload,
                    headers=self._auth_headers(),
               )

          if response.status_code in (200, 201):
               data = response.json()
               post = LinkedInPost(
                    author_urn=author_urn,
                    text=text,
                    hashtags=hashtags,
                    image_url=image_url,
                    linkedin_post_id=data.get("id"),
                    metadata=LinkedInPostMetadata(
                         posted=True,
                         posted_at=int(time.time()),
                         status=DeliverableStatus(status="completed"),
                    ),
               )
               return {"success": True, "post": post.model_dump()}

          return {"success": False, "status_code": response.status_code, "error": response.text}

     async def remove_linkedin_post(self, linkedin_post_id: str) -> dict:
          """Deletes a published LinkedIn post by its post ID."""
          if not self.access_token:
               await self.get_token()

          async with httpx.AsyncClient() as client:
               response = await client.delete(
                    f"https://api.linkedin.com/v2/ugcPosts/{linkedin_post_id}",
                    headers=self._auth_headers(),
               )

          if response.status_code == 204:
               metadata = LinkedInPostMetadata(
                    post_removed=True,
                    post_removed_at=int(time.time()),
                    status=DeliverableStatus(status="rejected"),
               )
               return {"success": True, "post_id": linkedin_post_id, "metadata": metadata.model_dump()}

          return {"success": False, "status_code": response.status_code, "error": response.text}

     async def edit_linkedin_post(self, linkedin_post_id: str, text: str, hashtags: list[str] = []) -> dict:
          """Edits the text and hashtags of an existing LinkedIn post."""
          if not self.access_token:
               await self.get_token()

          if hashtags:
               tag_string = " ".join(f"#{tag}" for tag in hashtags)
               text = f"{text}\n\n{tag_string}"

          encoded_id = urllib.parse.quote(linkedin_post_id, safe="")
          payload = {
               "patch": {
                    "$set": {
                         "specificContent": {
                              "com.linkedin.ugc.ShareContent": {
                                   "shareCommentary": {"text": text}
                              }
                         }
                    }
               }
          }

          async with httpx.AsyncClient() as client:
               response = await client.post(
                    f"https://api.linkedin.com/v2/ugcPosts/{encoded_id}",
                    json=payload,
                    headers={**self._auth_headers(), "X-RestLi-Method": "PARTIAL_UPDATE"},
               )

          if response.status_code == 204:
               metadata = LinkedInPostMetadata(
                    updated_at=int(time.time()),
               )
               return {"success": True, "post_id": linkedin_post_id, "metadata": metadata.model_dump()}

          return {"success": False, "status_code": response.status_code, "error": response.text}