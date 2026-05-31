import uuid

class LinkedInAccount:
     def __init__(self, id, account_id, name, author_urn, email, access_token=None, token_expires_at=None):
          self.id = id or str(uuid.uuid4())
          self.account_id = account_id      # LinkedIn member URN
          self.name = name
          self.author_urn = author_urn
          self.email = email
          self.access_token = access_token
          self.token_expires_at = token_expires_at

     def __repr__(self):
          return (
               f"<LinkedInAccount(id={self.id}, account_id={self.account_id}, "
               f"name='{self.name}', email='{self.email}')>"
          )