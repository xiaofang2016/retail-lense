FROM public.ecr.aws/lambda/python:3.12
WORKDIR ${LAMBDA_TASK_ROOT}

# Install third-party dependencies used by the auth Lambda.
COPY lambda_signin/requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN python -m pip install \
	--disable-pip-version-check \
	--no-compile \
	--no-cache-dir \
	-r ${LAMBDA_TASK_ROOT}/requirements.txt \
	-t ${LAMBDA_TASK_ROOT} \
 && rm -f ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy only application modules reached by the auth Lambda handler.
COPY core/exceptions.py ${LAMBDA_TASK_ROOT}/core/
COPY core/settings.py ${LAMBDA_TASK_ROOT}/core/
COPY core/security/__init__.py ${LAMBDA_TASK_ROOT}/core/security/
COPY core/security/hasher.py ${LAMBDA_TASK_ROOT}/core/security/
COPY core/security/tokens.py ${LAMBDA_TASK_ROOT}/core/security/
COPY core/security/ip.py ${LAMBDA_TASK_ROOT}/core/security/

COPY schema/auth.py ${LAMBDA_TASK_ROOT}/schema/
COPY schema/user.py ${LAMBDA_TASK_ROOT}/schema/

COPY services/__init__.py ${LAMBDA_TASK_ROOT}/services/
COPY services/auth_service.py ${LAMBDA_TASK_ROOT}/services/
COPY services/registration.py ${LAMBDA_TASK_ROOT}/services/
COPY services/user_store.py ${LAMBDA_TASK_ROOT}/services/
COPY services/two_factor.py ${LAMBDA_TASK_ROOT}/services/
COPY services/sns.py ${LAMBDA_TASK_ROOT}/services/
COPY services/dynamodb.py ${LAMBDA_TASK_ROOT}/services/
COPY services/secrets.py ${LAMBDA_TASK_ROOT}/services/

COPY lambda_signin/__init__.py ${LAMBDA_TASK_ROOT}/lambda_signin/
COPY lambda_signin/handler.py ${LAMBDA_TASK_ROOT}/lambda_signin/

# Ensure package markers exist for copied directories.
RUN touch ${LAMBDA_TASK_ROOT}/core/__init__.py ${LAMBDA_TASK_ROOT}/schema/__init__.py

CMD ["lambda_signin.handler.lambda_handler"]