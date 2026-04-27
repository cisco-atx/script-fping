"""
Fping routes module.

Provides the FpingScript class for handling user input and executing
fping collection tasks across network devices. It validates inputs,
renders templates, and triggers worker execution.

File path: routes.py
"""
import logging
import os

from flask import render_template_string

from .workers import run_fping

logger = logging.getLogger(__name__)


class FpingScript:
    meta = {
        "name": "Fping",
        "version": "1.0.0",
        "description": "Check IP reachability and resolve hostnames using fping",
        "icon": "network_ping",
    }

    def __init__(self, ctx=None):
        """Initialize FpingScript with context."""
        self.ctx = ctx

    @classmethod
    def required(self):
        return ["connector"]

    @classmethod
    def input(self):
        """Render input HTML template."""
        input_template = os.path.join(
            os.path.dirname(__file__),
            "templates",
            "input.html",
        )

        try:
            with open(input_template, encoding="utf-8") as file:
                template_content = file.read()
            return render_template_string(template_content)
        except Exception:
            logger.exception("Failed to load input template")
            raise

    def run(self, inputs):
        """Execute fping collection based on user inputs."""
        subnets = [
            subnet.strip()
            for subnet in inputs.get("subnets", "").splitlines()
            if subnet.strip()
        ]

        if not subnets:
            self.ctx.error("No IP Networks provided")
            return

        connector = self.ctx.config.get("connector", {})
        if not connector:
            self.ctx.error("No Connector information provided")
            return

        fqdn = inputs.get("fqdn", "")
        filters = inputs.get("filters", "")

        try:
            run_fping(
                subnets=subnets,
                fqdn=fqdn,
                filters=filters,
                connector=connector,
                ctx=self.ctx,
            )
        except Exception:
            raise
        self.ctx.finish()
