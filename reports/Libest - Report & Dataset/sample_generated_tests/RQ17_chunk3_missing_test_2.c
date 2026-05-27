/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk3_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include <string.h>
#include <stdlib.h>
#include "est.h"

/*
 * Externs used by existing tests / server callback instrumentation
 * (visible in exemplars/supporting code). These are shared across
 * the tests in this file.
 */
extern char tst_srvr_path_seg_cacerts[EST_MAX_PATH_SEGMENT_LEN + 1];

void rq17_chunk3_missing_test_2(void)
{
    EST_CTX *ectx = NULL;
    int rc = 0;
    int retrieved_cacerts_len = 0;
    char *retrieved_cacerts = NULL;
    const char *path_seg = "test-seg-123";

    /*
     * Initialize client context (variables like 'cacerts', 'cacerts_len',
     * and 'priv_key' are provided by the test harness / exemplars).
     */
    ectx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM,
                           client_manual_cert_verify);
    CU_ASSERT(ectx != NULL);

    rc = est_client_set_auth(ectx, "", "", NULL, priv_key);
    CU_ASSERT(rc == EST_ERR_NONE);

    /*
     * Case 1: no path-segment configured -> server should see an empty path_seg
     * Clear the instrumentation global then perform the GET.
     */
    est_client_set_server(ectx, US3512_SERVER_IP, US3512_SERVER_PORT, NULL);
    memset(tst_srvr_path_seg_cacerts, 0, EST_MAX_PATH_SEGMENT_LEN + 1);

    rc = est_client_get_cacerts(ectx, &retrieved_cacerts_len);
    CU_ASSERT(rc == EST_ERR_NONE);
    CU_ASSERT(retrieved_cacerts_len > 0);

    /* ensure server-observed path-seg is empty when none configured */
    CU_ASSERT(strlen(tst_srvr_path_seg_cacerts) == 0);

    retrieved_cacerts = malloc(retrieved_cacerts_len);
    CU_ASSERT(retrieved_cacerts != NULL);
    rc = est_client_copy_cacerts(ectx, retrieved_cacerts);
    CU_ASSERT(rc == EST_ERR_NONE);
    free(retrieved_cacerts);

    /*
     * Case 2: configured path-segment -> server should observe that segment
     */
    est_client_set_server(ectx, US3512_SERVER_IP, US3512_SERVER_PORT,
                          (char *)path_seg);
    memset(tst_srvr_path_seg_cacerts, 0, EST_MAX_PATH_SEGMENT_LEN + 1);

    rc = est_client_get_cacerts(ectx, &retrieved_cacerts_len);
    CU_ASSERT(rc == EST_ERR_NONE);
    CU_ASSERT(retrieved_cacerts_len > 0);

    /* verify the server received the configured path-seg for the cacerts request */
    CU_ASSERT(strcmp(tst_srvr_path_seg_cacerts, path_seg) == 0);

    if (ectx) {
        est_destroy(ectx);
    }
}
