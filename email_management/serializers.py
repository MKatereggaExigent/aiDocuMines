from __future__ import annotations

from rest_framework import serializers

from .models import EmailTemplate, OutboxEmail, EmailAttachment
from .utils import render_template, normalize_addresses


class EmailAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailAttachment
        fields = ["id", "uploaded", "filename", "mime_type", "size", "core_file", "created_at"]
        read_only_fields = ["id", "size", "created_at"]


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = [
            "id", "code", "name", "description",
            "subject_template", "body_text_template", "body_html_template",
            "is_active", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        req = self.context.get("request")
        if req and req.user and req.user.is_authenticated:
            validated_data["created_by"] = req.user
        return super().create(validated_data)


class OutboxEmailSerializer(serializers.ModelSerializer):
    attachments = EmailAttachmentSerializer(many=True, required=False)

    class Meta:
        model = OutboxEmail
        fields = [
            "id", "user", "client_id", "template", "context",
            "email_type",
            "from_email", "reply_to", "headers",
            "to", "cc", "bcc",
            "subject", "body_text", "body_html",
            "attachments",
            "scheduled_at", "status", "priority",
            "attempt_count", "max_attempts", "last_attempt_at",
            "last_error", "message_id", "provider_id",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "status", "attempt_count", "last_attempt_at",
            "last_error", "message_id", "provider_id",
            "created_at", "updated_at",
        ]

    def validate(self, attrs):
        template = attrs.get("template") or getattr(self.instance, "template", None)
        subject = attrs.get("subject") or getattr(self.instance, "subject", "")
        body_text = attrs.get("body_text") or getattr(self.instance, "body_text", "")
        body_html = attrs.get("body_html") or getattr(self.instance, "body_html", "")

        if not template and not (subject and (body_text or body_html)):
            raise serializers.ValidationError(
                "Provide either a template (with context) or a subject plus body_text/body_html."
            )
        return attrs

    def create(self, validated):
        atts = validated.pop("attachments", [])
        # Normalize address arrays if provided
        for key in ("to", "cc", "bcc", "reply_to"):
            if key in validated:
                validated[key] = normalize_addresses(validated[key])

        out = OutboxEmail.objects.create(**validated)
        for att in atts:
            a = EmailAttachment.objects.create(**att)
            out.attachments.add(a)

        return out

    def update(self, instance, validated):
        atts = validated.pop("attachments", None)
        for k, v in validated.items():
            setattr(instance, k, v)
        instance.save()

        if atts is not None:
            instance.attachments.clear()
            for att in atts:
                a = EmailAttachment.objects.create(**att)
                instance.attachments.add(a)
        return instance


class RenderPreviewSerializer(serializers.Serializer):
    template_code = serializers.SlugField()
    context = serializers.JSONField(default=dict)

    def validate(self, attrs):
        try:
            attrs["template_obj"] = EmailTemplate.objects.get(code=attrs["template_code"], is_active=True)
        except EmailTemplate.DoesNotExist:
            raise serializers.ValidationError("Unknown or inactive template_code.")
        return attrs

    def create(self, validated):
        t = validated["template_obj"]
        subj, text, html = render_template(t, validated.get("context") or {})
        return {"subject": subj, "body_text": text, "body_html": html}


# -------------------------
# Write serializer (create)
# -------------------------
class OutboxEmailCreateSerializer(serializers.ModelSerializer):
    # Accept either template id (template) or its slug (template_code)
    template_code = serializers.SlugField(write_only=True, required=False, allow_blank=False)
    attachments = EmailAttachmentSerializer(many=True, required=False)

    class Meta:
        model = OutboxEmail
        fields = [
            # addressing
            "to", "cc", "bcc", "reply_to",
            "from_email", "headers",

            # raw content path
            "subject", "body_text", "body_html",

            # template path
            "template", "template_code", "context",

            # classification / scheduling
            "email_type", "priority", "scheduled_at",

            # attachments (nested create)
            "attachments",
        ]

    def validate(self, attrs):
        # Resolve template_code -> template instance
        template = attrs.get("template")
        template_code = self.initial_data.get("template_code")
        if not template and template_code:
            try:
                attrs["template"] = EmailTemplate.objects.get(code=template_code, is_active=True)
            except EmailTemplate.DoesNotExist:
                raise serializers.ValidationError({"template_code": "Unknown template code."})

        has_template = bool(attrs.get("template"))
        has_raw = bool(attrs.get("subject")) and bool(attrs.get("body_text") or attrs.get("body_html"))

        if not has_template and not has_raw:
            raise serializers.ValidationError(
                "Provide either a template (with context) or a subject plus body_text/body_html."
            )
        return attrs

    def create(self, validated):
        # Never pass write-only alias to the model
        validated.pop("template_code", None)

        # Extract and handle M2M separately
        atts = validated.pop("attachments", [])

        # Normalize address arrays
        for key in ("to", "cc", "bcc", "reply_to"):
            if key in validated:
                validated[key] = normalize_addresses(validated[key])

        out = OutboxEmail.objects.create(**validated)

        # Create/add attachments if any
        for att in atts:
            a = EmailAttachment.objects.create(**att)
            out.attachments.add(a)

        return out

