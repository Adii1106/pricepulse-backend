from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL", "pricepulse@example.com")
        self.sg = SendGridAPIClient(self.sendgrid_api_key)

    def send_price_alert(self, to_email: str, product_name: str, current_price: float, 
                        target_price: float, product_url: str, image_url: str = None):
        """
        Send a price alert email when a product's price drops below the target price
        """
        try:
            subject = f"Price Alert: {product_name} is now below your target price!"
            
            # Create HTML content
            html_content = f"""
            <html>
                <body>
                    <h2>Price Alert!</h2>
                    <p>The price of <strong>{product_name}</strong> has dropped below your target price!</p>
                    
                    <div style="margin: 20px 0;">
                        <p><strong>Current Price:</strong> ₹{current_price}</p>
                        <p><strong>Your Target Price:</strong> ₹{target_price}</p>
                    </div>
                    
                    {f'<img src="{image_url}" alt="{product_name}" style="max-width: 300px; margin: 20px 0;">' if image_url else ''}
                    
                    <p>
                        <a href="{product_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; 
                        text-decoration: none; border-radius: 5px;">View Product</a>
                    </p>
                    
                    <p>Happy Shopping!</p>
                    <p>PricePulse Team</p>
                </body>
            </html>
            """
            
            # Create plain text content
            text_content = f"""
            Price Alert!
            
            The price of {product_name} has dropped below your target price!
            
            Current Price: ₹{current_price}
            Your Target Price: ₹{target_price}
            
            View the product here: {product_url}
            
            Happy Shopping!
            PricePulse Team
            """
            
            # Create message
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content),
                plain_text_content=Content("text/plain", text_content)
            )
            
            # Send email
            response = self.sg.send(message)
            logger.info(f"Price alert email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending price alert email: {str(e)}")
            return False 