from __future__ import annotations

import smtplib
import socket
import time
from email.message import EmailMessage


class SmtpMailer:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool = False,
        starttls: bool = True,
        timeout_s: int = 30,
        max_retries: int = 3,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.starttls = starttls
        self.timeout_s = timeout_s
        self.max_retries = max_retries

    def send(
        self,
        mail_from: str,
        mail_to: list[str],
        subject: str,
        text: str,
        html: str | None = None,
    ) -> None:
        msg = EmailMessage()
        msg["From"] = mail_from
        msg["To"] = ", ".join(mail_to)
        msg["Subject"] = subject
        msg.set_content(text)
        if html:
            msg.add_alternative(html, subtype="html")

        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                if self.use_ssl:
                    server: smtplib.SMTP = smtplib.SMTP_SSL(
                        self.host, self.port, timeout=self.timeout_s
                    )
                else:
                    server = smtplib.SMTP(self.host, self.port, timeout=self.timeout_s)

                with server:
                    server.ehlo()
                    if (not self.use_ssl) and self.starttls:
                        server.starttls()
                        server.ehlo()
                    server.login(self.username, self.password)
                    server.send_message(msg)
                return
            except (smtplib.SMTPException, socket.timeout, OSError) as e:
                last_err = e
                if attempt == self.max_retries:
                    break
                sleep_s = min(8.0, 0.8 * (2 ** (attempt - 1))) + (0.05 * attempt)
                time.sleep(sleep_s)
        assert last_err is not None
        raise last_err

