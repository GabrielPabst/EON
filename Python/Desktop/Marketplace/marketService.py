from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import requests
import io



class MakrosAPIClient:
    """
    Python client service for the Makros API.
    Handles authentication and provides methods for all API endpoints.
    """
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        Initialize the Makros API client.
        
        Args:
            base_url: The base URL of the API server
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {"Content-Type": "application/json"}
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and raise exceptions for errors."""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            try:
                error_msg = response.json().get('error', str(e))
            except:
                pass
            raise Exception(error_msg)

    # Authentication Methods
    
    def register(self, name: str, password: str) -> Dict[str, Any]:
        """
        Register a new account.
        
        Args:
            name: Account name/username
            password: Account password
            
        Returns:
            Dictionary containing account information
            
        Raises:
            Exception: If registration fails
        """
        url = f"{self.base_url}/api/accounts/register"
        data = {"name": name, "password": password}
        
        response = self.session.post(url, json=data, headers=self._get_headers())
        return self._handle_response(response)
    
    def login(self, name: str, password: str) -> Dict[str, Any]:
        """
        Login to the account.
        
        Args:
            name: Account name/username
            password: Account password
            
        Returns:
            Dictionary containing account info
            
        Raises:
            Exception: If login fails
        """
        url = f"{self.base_url}/api/accounts/login"
        data = {"name": name, "password": password}
        
        response = self.session.post(url, json=data, headers=self._get_headers())
        return self._handle_response(response)
    
    def logout(self):
        """Logout from the current session."""
        url = f"{self.base_url}/api/accounts/logout"
        response = self.session.post(url, headers=self._get_headers())
        self._handle_response(response)

    # Account Management Methods
    
    def get_account_data(self) -> Dict[str, Any]:
        """
        Get current account data.
        
        Returns:
            Dictionary containing account information
            
        Raises:
            Exception: If request fails or user not authenticated
        """
        url = f"{self.base_url}/api/accounts/data"
        response = self.session.get(url, headers=self._get_headers())
        return self._handle_response(response)
    
    def update_account(self, name: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Update account information.
        
        Args:
            name: New account name (optional)
            password: New password (optional)
            
        Returns:
            Dictionary containing updated account information
            
        Raises:
            Exception: If update fails or user not authenticated
        """
        url = f"{self.base_url}/api/accounts/data"
        data = {}
        if name is not None:
            data['name'] = name
        if password is not None:
            data['password'] = password
            
        response = self.session.put(url, json=data, headers=self._get_headers())
        return self._handle_response(response)

    # Makro Management Methods
    
    def upload_makro(self, file_path: Union[str, Path, io.BytesIO], name: str, 
                    desc: Optional[str] = None, usecase: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a new makro (ZIP file).
        
        Args:
            file_path: Path to ZIP file or BytesIO object
            name: Makro name
            desc: Makro description (optional)
            usecase: Makro use case (optional)
            
        Returns:
            Dictionary containing makro information
            
        Raises:
            Exception: If upload fails or user not authenticated
        """
        url = f"{self.base_url}/api/makros"
        
        # Prepare form data
        files = {}
        data = {"name": name}
        
        if desc is not None:
            data['desc'] = desc
        if usecase is not None:
            data['usecase'] = usecase
        
        # Handle file input
        if isinstance(file_path, io.BytesIO):
            files['file'] = ('makro.zip', file_path, 'application/zip')
        else:
            file_path = Path(file_path)
            with open(file_path, 'rb') as f:
                files['file'] = (file_path.name, f, 'application/zip')
        
        try:
            response = self.session.post(url, data=data, files=files)
            return self._handle_response(response)
        finally:
            for file_tuple in files.values():
                if hasattr(file_tuple[1], 'close'):
                    file_tuple[1].close()
    
    def get_makro(self, makro_id: int) -> Dict[str, Any]:
        """
        Get makro details by ID.
        
        Args:
            makro_id: ID of the makro
            
        Returns:
            Dictionary containing makro information
            
        Raises:
            Exception: If makro not found
        """
        url = f"{self.base_url}/api/makros/{makro_id}"
        response = self.session.get(url)
        return self._handle_response(response)
    
    def update_makro(self, makro_id: int, name: Optional[str] = None, 
                    desc: Optional[str] = None, usecase: Optional[str] = None) -> Dict[str, Any]:
        """
        Update makro information.
        
        Args:
            makro_id: ID of the makro to update
            name: New makro name (optional)
            desc: New makro description (optional)
            usecase: New makro use case (optional)
            
        Returns:
            Dictionary containing updated makro information
            
        Raises:
            Exception: If update fails, unauthorized, or makro not found
        """
        url = f"{self.base_url}/api/makros/{makro_id}"
        data = {}
        if name is not None:
            data['name'] = name
        if desc is not None:
            data['desc'] = desc
        if usecase is not None:
            data['usecase'] = usecase
            
        response = self.session.put(url, json=data, headers=self._get_headers())
        return self._handle_response(response)
    
    def delete_makro(self, makro_id: int) -> Dict[str, Any]:
        """
        Delete a makro.
        
        Args:
            makro_id: ID of the makro to delete
            
        Returns:
            Dictionary containing deletion confirmation
            
        Raises:
            Exception: If deletion fails, unauthorized, or makro not found
        """
        url = f"{self.base_url}/api/makros/{makro_id}"
        response = self.session.delete(url, headers=self._get_headers())
        return self._handle_response(response)
    
    def download_makro(self, makro_id: int, save_path: Optional[Union[str, Path]] = None) -> bytes:
        """
        Download makro file.
        
        Args:
            makro_id: ID of the makro to download
            save_path: Path to save the file (optional)
            
        Returns:
            File content as bytes
            
        Raises:
            Exception: If download fails or makro not found
        """
        url = f"{self.base_url}/api/makros/{makro_id}/download"
        response = self.session.get(url)
        
        if response.status_code != 200:
            self._handle_response(response)
        
        content = response.content
        
        if save_path:
            save_path = Path(save_path)
            save_path.write_bytes(content)
            
        return content

    # Marketplace Methods
    
    def list_marketplace_makros(self, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        List all makros in the marketplace (paginated).
        
        Args:
            page: Page number (default: 1)
            per_page: Items per page (default: 10)
            
        Returns:
            Dictionary containing paginated makros list
        """
        url = f"{self.base_url}/api/marketplace"
        params = {"page": page, "per_page": per_page}
        
        response = self.session.get(url, params=params)
        return self._handle_response(response)
    
    def get_random_makros(self, count: int = 5) -> Dict[str, Any]:
        """
        Get random makros from the marketplace.
        
        Args:
            count: Number of random makros to retrieve (default: 5)
            
        Returns:
            Dictionary containing random makros list
        """
        url = f"{self.base_url}/api/marketplace/random"
        params = {"count": count}
        
        response = self.session.get(url, params=params)
        return self._handle_response(response)
    
    def search_makros(self, query: Optional[str] = None, usecase: Optional[str] = None,
                     author: Optional[str] = None, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        Search for makros.
        
        Args:
            query: Search query (optional)
            usecase: Filter by usecase (optional)
            author: Filter by author name (optional)
            page: Page number (default: 1)
            per_page: Items per page (default: 10)
            
        Returns:
            Dictionary containing search results
        """
        url = f"{self.base_url}/api/marketplace/search"
        params = {
            "page": page,
            "per_page": per_page
        }
        
        if query:
            params["q"] = query
        if usecase:
            params["usecase"] = usecase
        if author:
            params["author"] = author
            
        response = self.session.get(url, params=params)
        return self._handle_response(response)
    
    def list_my_makros(self, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        List current user's makros.
        
        Args:
            page: Page number (default: 1)
            per_page: Items per page (default: 10)
            
        Returns:
            Dictionary containing paginated makros list
            
        Raises:
            Exception: If user not authenticated
        """
        url = f"{self.base_url}/api/my-makros"
        params = {"page": page, "per_page": per_page}
        
        response = self.session.get(url, params=params)
        return self._handle_response(response)


# Example usage
if __name__ == "__main__":
    # Initialize the client
    client = MakrosAPIClient("http://localhost:5000")
    
    try:
        print("\n=== Testing Authentication ===")
        # Register a new account (uncomment if needed)
        #account = client.register("testuser2", "password123")
        #print("Registered:", account)
        
        # Login
        login_result = client.login("testuser2", "password123")
        print("Logged in:", login_result)
        
        print("\n=== Testing Account Management ===")
        # Get account data
        account_data = client.get_account_data()
        print("Account data:", account_data)
        
        # Update account (optional)
        #updated_account = client.update_account(name="testuser2_updated")
        #print("Updated account:", updated_account)
        
        print("\n=== Testing Makro Management ===")
        # Upload a makro
        with open("example.zip", "rb") as f:
            makro = client.upload_makro(
                io.BytesIO(f.read()),
                name="Test Makro",
                desc="A test makro",
                usecase="Testing"
            )
            print("Uploaded makro:", makro)
            makro_id = makro['makro']['id']
            print("Makro ID:", makro_id)
            
            
            # Get makro details
            makro_details = client.get_makro(makro_id)
            print("Makro details:", makro_details)
            
            # Update makro
            updated_makro = client.update_makro(makro_id, desc="Updated test makro")
            print("Updated makro:", updated_makro)
            
            # Download makro
            content = client.download_makro(makro_id)
            print(f"Downloaded makro (size: {len(content)} bytes)")
            
        print("\n=== Testing Marketplace Features ===")
        # List marketplace makros
        marketplace_makros = client.list_marketplace_makros(page=1, per_page=5)
        print("Marketplace makros:", marketplace_makros)
        
        # Get random makros
        random_makros = client.get_random_makros(count=3)
        print("Random makros:", random_makros)
        
        # Search for makros
        search_results = client.search_makros(query="test", usecase="Testing", per_page=5)
        print("Search results:", search_results)
        
        # List my makros
        my_makros = client.list_my_makros(per_page=5)
        print("My makros:", my_makros)
        
        # Delete the test makro
        delete_result = client.delete_makro(makro_id)
        print("Delete result:", delete_result)
        
        print("\n=== Cleanup ===")
        # Logout
        client.logout()
        print("Logged out successfully")
        
    except Exception as e:
        print("Error:", str(e))
