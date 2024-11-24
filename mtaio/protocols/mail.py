"""
Asynchronous mail client implementation.

This module provides async wrappers for IMAP and SMTP protocols:

* AsyncIMAPClient: Async IMAP client
* AsyncSMTPClient: Async SMTP client
* MailMessage: Email message container
* Attachment: Email attachment wrapper
"""

from typing import List, Optional, Union, BinaryIO
from dataclasses import dataclass
import asyncio
import email
import imaplib
import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from ..exceptions import MailError


@dataclass
class Attachment:
    """
    Email attachment container.

    :param filename: Name of the file
    :type filename: str
    :param content: File content
    :type content: Union[str, bytes, BinaryIO]
    :param content_type: MIME content type
    :type content_type: str
    """

    filename: str
    content: Union[str, bytes, BinaryIO]
    content_type: str = "application/octet-stream"

    async def to_mime_part(self) -> MIMEApplication:
        """Convert to MIME part."""
        if isinstance(self.content, (str, bytes)):
            content = self.content
            if isinstance(content, str):
                content = content.encode("utf-8")
        else:
            content = await asyncio.to_thread(self.content.read)
            if isinstance(content, str):
                content = content.encode("utf-8")

        part = MIMEApplication(content, _subtype=self.content_type.split("/")[-1])
        part.add_header("Content-Disposition", "attachment", filename=self.filename)
        return part


@dataclass
class MailMessage:
    """
    Email message container.

    :param subject: Email subject
    :type subject: str
    :param sender: Sender email address
    :type sender: str
    :param recipients: List of recipient addresses
    :type recipients: List[str]
    :param text_content: Plain text content
    :type text_content: Optional[str]
    :param html_content: HTML content
    :type html_content: Optional[str]
    :param attachments: List of attachments
    :type attachments: List[Attachment]
    """

    subject: str
    sender: str
    recipients: List[str]
    text_content: Optional[str] = None
    html_content: Optional[str] = None
    attachments: List[Attachment] = None
    cc: List[str] = None
    bcc: List[str] = None
    reply_to: Optional[str] = None

    async def to_mime_message(self) -> EmailMessage:
        """Convert to MIME message."""
        message = MIMEMultipart("alternative")
        message["Subject"] = self.subject
        message["From"] = self.sender
        message["To"] = ", ".join(self.recipients)

        if self.cc:
            message["Cc"] = ", ".join(self.cc)
        if self.bcc:
            message["Bcc"] = ", ".join(self.bcc)
        if self.reply_to:
            message["Reply-To"] = self.reply_to

        # Add text content
        if self.text_content:
            message.attach(MIMEText(self.text_content, "plain"))

        # Add HTML content
        if self.html_content:
            message.attach(MIMEText(self.html_content, "html"))

        # Add attachments
        if self.attachments:
            for attachment in self.attachments:
                part = await attachment.to_mime_part()
                message.attach(part)

        return message

    @classmethod
    def parse_mime_message(cls, mime_message: EmailMessage) -> "MailMessage":
        """Parse MIME message into MailMessage."""
        subject = mime_message.get("Subject", "")
        sender = mime_message.get("From", "")
        recipients = [addr.strip() for addr in mime_message.get("To", "").split(",")]
        cc = [addr.strip() for addr in mime_message.get("Cc", "").split(",") if addr]
        bcc = [addr.strip() for addr in mime_message.get("Bcc", "").split(",") if addr]
        reply_to = mime_message.get("Reply-To")

        text_content = None
        html_content = None
        attachments = []

        for part in mime_message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                text_content = part.get_payload(decode=True).decode()
            elif content_type == "text/html":
                html_content = part.get_payload(decode=True).decode()
            elif part.get_filename():
                attachments.append(
                    Attachment(
                        filename=part.get_filename(),
                        content=part.get_payload(decode=True),
                        content_type=content_type,
                    )
                )

        return cls(
            subject=subject,
            sender=sender,
            recipients=recipients,
            text_content=text_content,
            html_content=html_content,
            attachments=attachments,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
        )


class AsyncIMAPClient:
    """
    Asynchronous IMAP client.

    Example::

        client = AsyncIMAPClient()
        await client.connect("imap.gmail.com", 993)
        await client.login("user@gmail.com", "password")
        messages = await client.fetch_messages()
    """

    def __init__(self):
        """Initialize IMAP client."""
        self._client = imaplib.IMAP4_SSL
        self._connection = None
        self._loop = asyncio.get_event_loop()

    async def connect(self, host: str, port: int = 993, use_ssl: bool = True) -> None:
        """
        Connect to IMAP server.

        :param host: Server hostname
        :type host: str
        :param port: Server port
        :type port: int
        :param use_ssl: Whether to use SSL
        :type use_ssl: bool
        """
        try:
            client_class = imaplib.IMAP4_SSL if use_ssl else imaplib.IMAP4
            self._connection = await asyncio.to_thread(client_class, host, port)
        except Exception as e:
            raise MailError(f"Failed to connect to IMAP server: {str(e)}") from e

    async def login(self, username: str, password: str) -> None:
        """
        Login to IMAP server.

        :param username: Username
        :type username: str
        :param password: Password
        :type password: str
        """
        if not self._connection:
            raise MailError("Not connected to IMAP server")

        try:
            await asyncio.to_thread(self._connection.login, username, password)
        except Exception as e:
            raise MailError(f"IMAP login failed: {str(e)}") from e

    async def select_mailbox(self, mailbox: str = "INBOX") -> int:
        """
        Select mailbox/folder.

        :param mailbox: Mailbox name
        :type mailbox: str
        :return: Number of messages in mailbox
        :rtype: int
        """
        if not self._connection:
            raise MailError("Not connected to IMAP server")

        try:
            result, data = await asyncio.to_thread(self._connection.select, mailbox)
            if result != "OK":
                raise MailError(f"Failed to select mailbox: {result}")
            return int(data[0])
        except Exception as e:
            raise MailError(f"Failed to select mailbox: {str(e)}") from e

    async def fetch_messages(
        self, criteria: str = "ALL", limit: Optional[int] = None
    ) -> List[MailMessage]:
        """
        Fetch messages from current mailbox.

        :param criteria: Search criteria
        :type criteria: str
        :param limit: Maximum number of messages to fetch
        :type limit: Optional[int]
        :return: List of messages
        :rtype: List[MailMessage]
        """
        if not self._connection:
            raise MailError("Not connected to IMAP server")

        try:
            # Search for messages
            result, message_numbers = await asyncio.to_thread(
                self._connection.search, None, criteria
            )

            if result != "OK":
                raise MailError(f"Search failed: {result}")

            message_list = message_numbers[0].split()
            if limit:
                message_list = message_list[-limit:]

            messages = []
            for num in message_list:
                result, msg_data = await asyncio.to_thread(
                    self._connection.fetch, num, "(RFC822)"
                )

                if result != "OK":
                    continue

                email_body = msg_data[0][1]
                mime_message = email.message_from_bytes(email_body)
                messages.append(MailMessage.parse_mime_message(mime_message))

            return messages

        except Exception as e:
            raise MailError(f"Failed to fetch messages: {str(e)}") from e

    async def delete_messages(self, message_ids: List[str]) -> None:
        """
        Delete messages by ID.

        :param message_ids: List of message IDs
        :type message_ids: List[str]
        """
        if not self._connection:
            raise MailError("Not connected to IMAP server")

        try:
            for msg_id in message_ids:
                await asyncio.to_thread(
                    self._connection.store, msg_id, "+FLAGS", "\\Deleted"
                )
            await asyncio.to_thread(self._connection.expunge)
        except Exception as e:
            raise MailError(f"Failed to delete messages: {str(e)}") from e

    async def close(self) -> None:
        """Close connection."""
        if self._connection:
            try:
                await asyncio.to_thread(self._connection.logout)
            except Exception:
                pass
            finally:
                self._connection = None

    async def __aenter__(self) -> "AsyncIMAPClient":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()


class AsyncSMTPClient:
    """
    Asynchronous SMTP client.

    Example::

        client = AsyncSMTPClient()
        await client.connect("smtp.gmail.com", 587)
        await client.login("user@gmail.com", "password")
        await client.send_message(message)
    """

    def __init__(self):
        """Initialize SMTP client."""
        self._client = None
        self._loop = asyncio.get_event_loop()

    async def connect(self, host: str, port: int = 587, use_tls: bool = True) -> None:
        """
        Connect to SMTP server.

        :param host: Server hostname
        :type host: str
        :param port: Server port
        :type port: int
        :param use_tls: Whether to use TLS
        :type use_tls: bool
        """
        try:
            self._client = await asyncio.to_thread(smtplib.SMTP, host, port)
            if use_tls:
                await asyncio.to_thread(self._client.starttls)
        except Exception as e:
            raise MailError(f"Failed to connect to SMTP server: {str(e)}") from e

    async def login(self, username: str, password: str) -> None:
        """
        Login to SMTP server.

        :param username: Username
        :type username: str
        :param password: Password
        :type password: str
        """
        if not self._client:
            raise MailError("Not connected to SMTP server")

        try:
            await asyncio.to_thread(self._client.login, username, password)
        except Exception as e:
            raise MailError(f"SMTP login failed: {str(e)}") from e

    async def send_message(self, message: MailMessage) -> None:
        """
        Send email message.

        :param message: Message to send
        :type message: MailMessage
        """
        if not self._client:
            raise MailError("Not connected to SMTP server")

        try:
            mime_message = await message.to_mime_message()
            await asyncio.to_thread(self._client.send_message, mime_message)
        except Exception as e:
            raise MailError(f"Failed to send message: {str(e)}") from e

    async def close(self) -> None:
        """Close connection."""
        if self._client:
            try:
                await asyncio.to_thread(self._client.quit)
            except Exception:
                pass
            finally:
                self._client = None

    async def __aenter__(self) -> "AsyncSMTPClient":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()
