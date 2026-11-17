import boto3
from botocore.exceptions import ClientError

from odoo import api, models

print("===== MinIO Module Loaded =====")


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def _storage(self):
        storage = super()._storage()
        print("===================================")
        print("===== STORAGE TYPE =====")
        print(storage)
        print("===================================")
        return storage

    def _get_minio_client(self):
        return boto3.client(
            "s3",
            endpoint_url="http://localhost:9000",
            aws_access_key_id="minioadmin",
            aws_secret_access_key="minioadmin",
        )

    def _get_bucket_name(self):
        return "odoo"

    @api.model_create_multi
    def create(self, vals_list):
        print("===================================")
        print("===== CREATE METHOD CALLED =====")
        print(vals_list)
        print("===================================")

        records = super().create(vals_list)

        print("===== CREATE FINISHED =====")

        return records

    @api.model
    def _file_write(self, bin_value, checksum):
        print("===================================")
        print("===== _file_write CALLED =====")
        print("Checksum:", checksum)
        print("===================================")

        client = self._get_minio_client()

        try:
            client.put_object(
                Bucket=self._get_bucket_name(),
                Key=checksum,
                Body=bin_value,
            )

            print("===== Uploaded Successfully to MinIO =====")

        except Exception as e:
            print("===== ERROR Uploading to MinIO =====")
            print(str(e))
            raise

        return checksum

    @api.model
    def _file_read(self, fname):
        print("===================================")
        print("===== _file_read CALLED =====")
        print("File:", fname)
        print("===================================")

        client = self._get_minio_client()

        try:
            obj = client.get_object(
                Bucket=self._get_bucket_name(),
                Key=fname,
            )

            print("===== Downloaded From MinIO =====")

            return obj["Body"].read()

        except ClientError as e:
            print("===== File Not Found In MinIO =====")
            print(str(e))
            return b""

    @api.model
    def _file_delete(self, fname):
        print("===================================")
        print("===== _file_delete CALLED =====")
        print("File:", fname)
        print("===================================")

        client = self._get_minio_client()

        try:
            client.delete_object(
                Bucket=self._get_bucket_name(),
                Key=fname,
            )

            print("===== Deleted From MinIO =====")

        except ClientError as e:
            print("===== Delete Failed =====")
            print(str(e))

        return True