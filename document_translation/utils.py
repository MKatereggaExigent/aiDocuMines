import os
import logging
import configparser
import time
import uuid
from datetime import datetime, timedelta
from azure.storage.blob import (
    BlobServiceClient, generate_container_sas, ContainerSasPermissions
)
from azure.ai.translation.document import (
    DocumentTranslationClient, DocumentTranslationInput, TranslationTarget
)
from azure.core.credentials import AzureKeyCredential
from django.utils.timezone import now
from core.models import File
from document_translation.models import TranslationRun, TranslationFile
from dotenv import load_dotenv

from document_translation.models import TranslationLanguage

from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

# ✅ Load environment variables
load_dotenv()

# ✅ Logger setup
logger = logging.getLogger(__name__)


import os
import logging
import configparser
import time
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.translation.document import (
    DocumentTranslationClient, DocumentTranslationInput, TranslationTarget
)
from azure.storage.blob import (
    BlobServiceClient, generate_container_sas, ContainerSasPermissions
)
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from django.utils.timezone import now
from core.models import File
from document_translation.models import TranslationRun, TranslationFile

# ✅ Load environment variables
load_dotenv()

# ✅ Logger setup
logger = logging.getLogger(__name__)


class AzureBlobService:
    """Handles interaction with Azure Blob Storage securely."""

    def __init__(self):
        self.config = self.load_config()
        self.storage_account_name = self.config["storage_account_name"]
        self.storage_url = self.config["storage_url"].rstrip('/')
        self.storage_account_key = os.getenv("STORAGE_ACCOUNT_KEY")
        self.connection_string = os.getenv("CONNECTION_STRING")
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)

    def load_config(self):
        """Securely loads Azure storage configurations."""
        config_obj = configparser.ConfigParser()
        config_file = os.path.join(os.path.dirname(__file__), 'config.ini')
        if not os.path.exists(config_file):
            raise FileNotFoundError("❌ Configuration file 'config.ini' not found.")
        config_obj.read(config_file)
        client_name = "devtests"
        return {
            "storage_account_name": config_obj[client_name].get("storage_account_name"),
            "storage_url": config_obj[client_name].get("storage_url").rstrip('/'),
            "translator_document_endpoint": config_obj[client_name].get("translator_document_endpoint")
        }

    def ensure_container_exists(self, container_name):
        """Ensures a container exists, retrying if Azure is still deleting it."""
        container_client = self.blob_service_client.get_container_client(container_name)
        retries = 5

        while retries > 0:
            try:
                if container_client.exists():
                    logger.info(f"✅ Container '{container_name}' already exists.")
                    return
                logger.info(f"📂 Creating container: {container_name}")
                container_client.create_container()
                logger.info(f"✅ Created container: {container_name}")
                return
            except ResourceExistsError as e:
                if "ContainerBeingDeleted" in str(e):
                    logger.warning(f"⚠️ Container '{container_name}' is still being deleted. Retrying in 5 seconds...")
                    time.sleep(5)
                    retries -= 1
                else:
                    raise e
        raise Exception(f"❌ Failed to create container '{container_name}'. Container deletion is taking too long.")

    def force_delete_container(self, container_name):
        """Forcibly deletes an Azure Blob container after ensuring all files are removed."""
        container_client = self.blob_service_client.get_container_client(container_name)
        retries = 5
        while retries > 0:
            try:
                for blob in container_client.list_blobs():
                    container_client.delete_blob(blob.name)
                container_client.delete_container()
                logger.info(f"✅ Deleted container: {container_name}")
                return
            except ResourceExistsError:
                logger.warning(f"⚠️ Container '{container_name}' is still being deleted. Retrying in 5 seconds...")
                time.sleep(5)
                retries -= 1
        logger.error(f"❌ Failed to delete container '{container_name}' after multiple attempts.")

    def generate_sas_url(self, container_name):
        """Generates a SAS URL for a container."""
        sas_permissions = ContainerSasPermissions(read=True, write=True, delete=True, list=True, add=True, create=True)
        sas_token = generate_container_sas(
            self.storage_account_name, container_name,
            account_key=self.storage_account_key,
            permission=sas_permissions,
            start=datetime.utcnow(),
            expiry=datetime.utcnow() + timedelta(hours=2)
        )
        return f"{self.storage_url}/{container_name}?{sas_token}"

    def upload_file_if_not_exists(self, container_name, file_path):
        """Uploads a file to Azure Blob Storage only if it does not already exist."""
        file_name = os.path.basename(file_path)
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=file_name)

        if blob_client.exists():
            logger.info(f"✅ File '{file_name}' already exists in '{container_name}', skipping upload.")
            return

        logger.info(f"📤 Uploading '{file_name}' to Azure Blob Storage...")
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        logger.info(f"✅ Successfully uploaded '{file_name}' to '{container_name}'.")

    def download_files(self, container_name, destination_folder):
        """Downloads translated files from Azure Blob Storage."""
        output_container_client = self.blob_service_client.get_container_client(container_name)
        os.makedirs(destination_folder, exist_ok=True)

        for blob in output_container_client.list_blobs():
            blob_client_instance = self.blob_service_client.get_blob_client(container_name, blob.name)
            blob_data = blob_client_instance.download_blob()
            destination_file_path = os.path.join(destination_folder, blob.name)

            with open(destination_file_path, "wb") as my_blob:
                blob_data.readinto(my_blob)
            logger.info(f"✅ Downloaded: {destination_file_path}")
            
    def delete_container(self, container_name):
        """Deletes an Azure Blob Storage container."""
        container_client = self.blob_service_client.get_container_client(container_name)
        container_client.delete_container()
        logger.info(f"✅ Deleted container: {container_name}")


class TranslationService:
    """Handles document translation via Azure Document Translation API."""

    def __init__(self):
        self.azure_service = AzureBlobService()
        self.translator_document_key = os.getenv("TRANSLATOR_DOCUMENT_KEY")
        self.translator_document_endpoint = self.azure_service.config["translator_document_endpoint"]
        self.client = DocumentTranslationClient(
            self.translator_document_endpoint, AzureKeyCredential(self.translator_document_key)
        )

    def translate_file(self, file_id, run_id, source_language, target_language):
        """Translates a document using Azure Document Translation API."""
        original_file = File.objects.get(id=file_id)
        translation_run = TranslationRun.objects.get(id=run_id)

        translation_run.status = "Translating"
        translation_run.save()

        # Define Azure containers
        source_container = f"translation-source-{uuid.uuid4()}"
        target_container = f"translation-target-{uuid.uuid4()}"

        self.azure_service.ensure_container_exists(source_container)
        self.azure_service.ensure_container_exists(target_container)
        self.azure_service.upload_file_if_not_exists(source_container, original_file.filepath)

        source_sas_url = self.azure_service.generate_sas_url(source_container)
        target_sas_url = self.azure_service.generate_sas_url(target_container)

        translation_input = DocumentTranslationInput(
            source_url=source_sas_url,
            targets=[TranslationTarget(target_url=target_sas_url, language=target_language)]
        )
        self.client.begin_translation(inputs=[translation_input]).wait()

        # Store the translated file using the original filename
        translated_folder = os.path.join(os.path.dirname(original_file.filepath), "translations", target_language)
        os.makedirs(translated_folder, exist_ok=True)

        self.azure_service.download_files(target_container, translated_folder)

        # ✅ Preserve original filename
        translated_filename = os.path.basename(original_file.filepath)  # Keep original filename
        translated_filepath = os.path.join(translated_folder, translated_filename)

        # ✅ Update TranslationFile Model
        TranslationFile.objects.create(
            run=translation_run,  # Assigning the correct TranslationRun
            original_file=original_file,
            translated_filepath=translated_filepath,
            status="Completed"
        )

        translation_run.status = "Completed"
        translation_run.save()

        self.azure_service.force_delete_container(source_container)
        self.azure_service.force_delete_container(target_container)

        return {"file_id": file_id, "translated_file": translated_filepath, "status": "Completed"}



'''
class TranslationService:
    """Handles document translation via Azure Document Translation API."""

    def __init__(self):
        self.azure_service = AzureBlobService()
        self.translator_document_key = os.getenv("TRANSLATOR_DOCUMENT_KEY")
        self.translator_document_endpoint = self.azure_service.config["translator_document_endpoint"]
        self.client = DocumentTranslationClient(
            self.translator_document_endpoint, AzureKeyCredential(self.translator_document_key)
        )
    
    def translate_file(self, file_id, run_id, source_language, target_language):
        """Translates a document using Azure Document Translation API."""
        original_file = File.objects.get(id=file_id)
        translation_run = TranslationRun.objects.get(id=run_id)
    
        translation_run.status = "Translating"
        translation_run.save()
    
        # Define Azure containers
        source_container = f"translation-source-{uuid.uuid4()}"
        target_container = f"translation-target-{uuid.uuid4()}"
    
        self.azure_service.ensure_container_exists(source_container)
        self.azure_service.ensure_container_exists(target_container)
        self.azure_service.upload_file_if_not_exists(source_container, original_file.filepath)
    
        source_sas_url = self.azure_service.generate_sas_url(source_container)
        target_sas_url = self.azure_service.generate_sas_url(target_container)
    
        translation_input = DocumentTranslationInput(
            source_url=source_sas_url,
            targets=[TranslationTarget(target_url=target_sas_url, language=target_language)]
        )
        self.client.begin_translation(inputs=[translation_input]).wait()
    
        # Store the translated file using the original filename
        translated_folder = os.path.join(os.path.dirname(original_file.filepath), "translations", target_language)
        os.makedirs(translated_folder, exist_ok=True)
    
        self.azure_service.download_files(target_container, translated_folder)
    
        # ✅ Preserve original filename
        translated_filename = os.path.basename(original_file.filepath)  # Keep original filename
        translated_filepath = os.path.join(translated_folder, translated_filename)
    
        # ✅ Update TranslationFile Model
        TranslationFile.objects.create(
            run=translation_run,
            original_file=original_file,
            translated_filepath=translated_filepath,
            status="Completed"
        )
    
        translation_run.status = "Completed"
        translation_run.save()
    
        self.azure_service.force_delete_container(source_container)
        self.azure_service.force_delete_container(target_container)
    
        return {"file_id": file_id, "translated_file": translated_filepath, "status": "Completed"}
'''    

def load_translation_languages():
    """
    Ensures the `TranslationLanguage` table is populated at startup.
    Complete list from Azure Translator API:
    https://learn.microsoft.com/en-us/azure/ai-services/translator/language-support
    """
    language_data = [
        ("Afrikaans", "af"), ("Albanian", "sq"), ("Amharic", "am"), ("Arabic", "ar"),
        ("Armenian", "hy"), ("Assamese", "as"), ("Azerbaijani (Latin)", "az"), ("Bangla", "bn"),
        ("Bashkir", "ba"), ("Basque", "eu"), ("Bhojpuri", "bho"), ("Bodo", "brx"),
        ("Bosnian (Latin)", "bs"), ("Bulgarian", "bg"), ("Cantonese (Traditional)", "yue"),
        ("Catalan", "ca"), ("Chhattisgarhi", "hne"), ("Chinese (Literary)", "lzh"),
        ("Chinese Simplified", "zh-Hans"), ("Chinese Traditional", "zh-Hant"), ("chiShona", "sn"),
        ("Croatian", "hr"), ("Czech", "cs"), ("Danish", "da"), ("Dari", "prs"), ("Divehi", "dv"),
        ("Dogri", "doi"), ("Dutch", "nl"), ("English", "en"), ("Estonian", "et"), ("Faroese", "fo"),
        ("Fijian", "fj"), ("Filipino", "fil"), ("Finnish", "fi"), ("French", "fr"),
        ("French (Canada)", "fr-ca"), ("Galician", "gl"), ("Georgian", "ka"), ("German", "de"),
        ("Greek", "el"), ("Gujarati", "gu"), ("Haitian Creole", "ht"), ("Hausa", "ha"),
        ("Hebrew", "he"), ("Hindi", "hi"), ("Hmong Daw (Latin)", "mww"), ("Hungarian", "hu"),
        ("Icelandic", "is"), ("Igbo", "ig"), ("Indonesian", "id"), ("Inuinnaqtun", "ikt"),
        ("Inuktitut", "iu"), ("Inuktitut (Latin)", "iu-Latn"), ("Irish", "ga"), ("Italian", "it"),
        ("Japanese", "ja"), ("Kannada", "kn"), ("Kashmiri", "ks"), ("Kazakh", "kk"), ("Khmer", "km"),
        ("Kinyarwanda", "rw"), ("Klingon", "tlh-Latn"), ("Klingon (plqaD)", "tlh-Piqd"),
        ("Konkani", "gom"), ("Korean", "ko"), ("Kurdish (Central)", "ku"), ("Kurdish (Northern)", "kmr"),
        ("Kyrgyz (Cyrillic)", "ky"), ("Lao", "lo"), ("Latvian", "lv"), ("Lingala", "ln"),
        ("Lithuanian", "lt"), ("Lower Sorbian", "dsb"), ("Luganda", "lug"), ("Macedonian", "mk"),
        ("Maithili", "mai"), ("Malagasy", "mg"), ("Malay (Latin)", "ms"), ("Malayalam", "ml"),
        ("Maltese", "mt"), ("Manipuri", "mni"), ("Maori", "mi"), ("Marathi", "mr"),
        ("Mongolian (Cyrillic)", "mn-Cyrl"), ("Mongolian (Traditional)", "mn-Mong"),
        ("Myanmar", "my"), ("Nepali", "ne"), ("Norwegian Bokmål", "nb"), ("Nyanja", "nya"),
        ("Odia", "or"), ("Pashto", "ps"), ("Persian", "fa"), ("Polish", "pl"),
        ("Portuguese (Brazil)", "pt"), ("Portuguese (Portugal)", "pt-pt"), ("Punjabi", "pa"),
        ("Queretaro Otomi", "otq"), ("Romanian", "ro"), ("Rundi", "run"), ("Russian", "ru"),
        ("Samoan (Latin)", "sm"), ("Serbian (Cyrillic)", "sr-Cyrl"), ("Serbian (Latin)", "sr-Latn"),
        ("Sesotho", "st"), ("Sesotho sa Leboa", "nso"), ("Setswana", "tn"), ("Sindhi", "sd"),
        ("Sinhala", "si"), ("Slovak", "sk"), ("Slovenian", "sl"), ("Somali (Arabic)", "so"),
        ("Spanish", "es"), ("Swahili (Latin)", "sw"), ("Swedish", "sv"), ("Tahitian", "ty"),
        ("Tamil", "ta"), ("Tatar (Latin)", "tt"), ("Telugu", "te"), ("Thai", "th"),
        ("Tibetan", "bo"), ("Tigrinya", "ti"), ("Tongan", "to"), ("Turkish", "tr"),
        ("Turkmen (Latin)", "tk"), ("Ukrainian", "uk"), ("Upper Sorbian", "hsb"), ("Urdu", "ur"),
        ("Uyghur (Arabic)", "ug"), ("Uzbek (Latin)", "uz"), ("Vietnamese", "vi"), ("Welsh", "cy"),
        ("Xhosa", "xh"), ("Yoruba", "yo"), ("Yucatec Maya", "yua"), ("Zulu", "zu")
    ]

    # ✅ Ensure database is accessible before executing query
    try:
        if TranslationLanguage.objects.exists():
            logger.info("✅ Translation languages already exist. Skipping population.")
            return

        for name, code in language_data:
            TranslationLanguage.objects.get_or_create(name=name, code=code)

        logger.info("✅ Translation languages successfully populated.")

    except Exception as e:
        logger.error(f"❌ Error populating translation languages: {e}")

