/*
 * Generated from saved assertion gaps.
 * framework=generic c test
 * language=c
 * filename=RQ13_chunk10_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>
#include "est.h"

void rq13_chunk10_missing_test_2(void)
{
    unsigned char *cacerts = NULL;
    int cacerts_len = 0;
    void *ectx1 = NULL;
    void *ectx2 = NULL;
    int rv = 0;

    /* Load first trust-anchor DB and initialize client context */
    cacerts_len = read_binary_file("US899/test16trust.crt", &cacerts);
    CU_ASSERT(cacerts_len > 0);
    ectx1 = est_client_init(cacerts, cacerts_len,
                            EST_CERT_FORMAT_PEM,
                            client_manual_cert_verify);
    CU_ASSERT(ectx1 != NULL);
    rv = est_enable_crl(ectx1);
    CU_ASSERT(rv == EST_ERR_NONE);
    rv = est_client_set_auth(ectx1, "testuser", "testpwd", NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    /* Cleanup first context */
    est_destroy(ectx1);
    free(cacerts);
    cacerts = NULL;

    /* Load second trust-anchor DB (different trust-anchor composition) */
    cacerts_len = read_binary_file("US899/test17trust.crt", &cacerts);
    CU_ASSERT(cacerts_len > 0);
    ectx2 = est_client_init(cacerts, cacerts_len,
                            EST_CERT_FORMAT_PEM,
                            client_manual_cert_verify);
    CU_ASSERT(ectx2 != NULL);
    rv = est_enable_crl(ectx2);
    CU_ASSERT(rv == EST_ERR_NONE);
    rv = est_client_set_auth(ectx2, "testuser", "testpwd", NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    /* Cleanup second context */
    est_destroy(ectx2);
    free(cacerts);
}
