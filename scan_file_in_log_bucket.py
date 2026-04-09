import boto3

environment = (
    "qa" if ev_default_system_env not in ("prd", "dev") else ev_default_system_env
)
market = ev_default_market.lower()
log_s3_bucket_name = f"{environment}-externalsource-elma{market}-log"
context.updateVariable("jv_log_s3_bucket", log_s3_bucket_name)


log_folder_path = (
    f"disp_message/inbound/sa-{jv_output_tenant_name}-dcxinge/{jv_disp_job_name}/"
)
print(f"Checking message files in {log_s3_bucket_name}/{log_folder_path}")

"""Boto3 Variables"""
s3_client = boto3.client("s3")

parameters = {"Bucket": log_s3_bucket_name, "Prefix": log_folder_path}
print(parameters)
paginator = s3_client.get_paginator("list_objects_v2")
process_file_list = []
for page in paginator.paginate(**parameters):
    if "Contents" in page:
        for obj in page["Contents"]:
            if not obj["Key"].endswith("/"):
                if obj["Key"] in (
                    'disp_message/inbound/sa-edp_consumer-dcxinge/edp_consumer_dcs_consumer_dcs_dk_devices_lz/lz/20260323040000-bdc3d9cd-c827-4e52-857d-81949895f4b9.json' ## change here
                ):
                    process_file_list.append([obj["Key"]])

print(process_file_list)
context.updateGridVariable("gv_process_file", process_file_list)
num_of_files = len(process_file_list)
print(f"Number of file need to be processed: {num_of_files}")
for file in context.getGridVariable("gv_process_file"):
    print(file[0].split("/")[-1])
print(jv_table_name)
if num_of_files > 0:
    context.updateVariable("jv_file_exist_flag", "TRUE")
else:
    print("No file needs to be processed. Stop processing")
    context.updateVariable("jv_file_exist_flag", "FALSE")
