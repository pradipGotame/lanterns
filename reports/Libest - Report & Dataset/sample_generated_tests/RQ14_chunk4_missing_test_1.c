/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ14_chunk4_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include <string.h>

/* Project headers referenced by exemplar tests (functions/constants used below) */
#include "est_client.h"

/*
 * Note: This prelude provides the minimal includes and project header
 * references that the test function below relies upon (consistent with
 * exemplar test fragments). The test function assumes the common test
 * harness provides/initializes `ectx` as in the exemplars.
 */

void rq14_chunk4_missing_test_1(void)
{
    int rc_full_uri = -1;
    int rc_auth_port = -1;
    int rc_path_nonnull = -1;
    int rc_null = -1;
    int rc_empty = -1;

    /* Full operation URI supplied as the 'server' parameter */
    const char *full_op_uri = "https://www.example.com/.well-known/est/";

    /* Authority that includes an embedded port */
    const char *authority_with_port = "www.example.com:80";

    /* A valid non-NULL path segment (optional label form) */
    const char *path_seg = "arbitraryLabel1";

    /* Empty string path segment to compare semantics against NULL */
    const char *empty_seg = "";

    /*
     * The exemplar tests capture return codes from est_client_set_server
     * and assert them. Do the same for the full-URI form to verify it
     * is accepted by the client configuration API.
     */
    rc_full_uri = est_client_set_server(ectx, full_op_uri, 0, NULL);
    CU_ASSERT(rc_full_uri == EST_ERR_NONE);

    /* Verify authority string that includes a port is accepted */
    rc_auth_port = est_client_set_server(ectx, authority_with_port, 0, NULL);
    CU_ASSERT(rc_auth_port == EST_ERR_NONE);

    /* Verify that passing a valid non-NULL path_segment returns success */
    rc_path_nonnull = est_client_set_server(ectx, US3512_SERVER_IP, US3512_SERVER_PORT, (char *)path_seg);
    CU_ASSERT(rc_path_nonnull == EST_ERR_NONE);

    /* Distinguish semantics between NULL and empty-string path_segment by comparing return codes */
    rc_null = est_client_set_server(ectx, US3512_SERVER_IP, US3512_SERVER_PORT, NULL);
    rc_empty = est_client_set_server(ectx, US3512_SERVER_IP, US3512_SERVER_PORT, (char *)empty_seg);
    CU_ASSERT(rc_null == rc_empty);

    /* Cleanup consistent with exemplar tests */
    if (ectx) {
        est_destroy(ectx);
    }
}
