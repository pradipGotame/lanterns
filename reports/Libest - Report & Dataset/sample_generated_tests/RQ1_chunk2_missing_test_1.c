/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk2_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include <openssl/x509.h>
#include "est.h"
#include "est_server.h"

void rq1_chunk2_missing_test_1(void)
{
    int rc;
    /*
     * The est_set_ca_reenroll_cb function is provided by the server
     * implementation (see supporting est_server.c snippet). We call it
     * with a NULL context to verify the registration API exists and
     * returns an error for an invalid (NULL) context. This exercises
     * the callback-registration surface that is required for server->CA
     * communication handling.
     */
    rc = est_set_ca_reenroll_cb(NULL, NULL);
    /*
     * Expect a non-success value when called with a NULL context.
     * The project tests use EST_ERR_NONE as the success code, so
     * assert that we do not get success here.
     */
    CU_ASSERT(rc != EST_ERR_NONE);
}
