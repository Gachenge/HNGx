FROM rabbitmq:3.8.0-management

COPY rabbitmq.conf /etc/rabbitmq/

# Expose the RabbitMQ management console and default RabbitMQ port
EXPOSE 15672 5672

# Set environment variables for RabbitMQ
ENV RABBITMQ_NODENAME=rabbit@localhost
ENV RABBITMQ_DEFAULT_USER=myuser
ENV RABBITMQ_DEFAULT_PASS=mypassword

RUN chown rabbitmq:rabbitmq /etc/rabbitmq/rabbitmq.conf
USER rabbitmq:rabbitmq
