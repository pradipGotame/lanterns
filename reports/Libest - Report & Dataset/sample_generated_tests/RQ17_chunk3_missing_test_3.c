/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk3_missing_test_3.c
 */

#include <string.h>
#include <stdlib.h>
#include "CUnit/CUnit.h"
#include "est.h"

/*
 * Externs referenced by exemplar tests/body in the suite. These are
 * declared here so the test function below can reference the server-captured
 * buffers and common test fixtures used by other tests in the suite.
 */
extern char tst_srvr_path_seg_cacerts[EST_MAX_PATH_SEGMENT_LEN + 1];
extern unsigned char *cacerts;
extern int cacerts_len;
extern void *priv_key;

void rq17_chunk3_missing_test_3(void)
{
    void *ctx = NULL;
    int rc = 0;
    int retrieved_cacerts_len = 0;
    const char path_segment[] = "myPathSeg";

    /*
     * initialize client context as in exemplar tests
     */
    ctx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM,
                          client_manual_cert_verify);
    CU_ASSERT(ctx != NULL);

    rc = est_client_set_auth(ctx, "", "", NULL, priv_key);
    CU_ASSERT(rc == EST_ERR_NONE);

    /*
     * Case A: No path-seg configured. Clear server-captured path-seg buffer
     * and verify it remains empty after issuing GET /.well-known/est/cacerts
     */
    memset(tst_srvr_path_seg_cacerts, 0, EST_MAX_PATH_SEGMENT_LEN + 1);
    est_client_set_server(ctx, US896_SERVER_IP, US896_SERVER_PORT, NULL);

    rc = est_client_get_cacerts(ctx, &retrieved_cacerts_len);
    CU_ASSERT(rc == EST_ERR_NONE);
    CU_ASSERT(retrieved_cacerts_len > 0);

    /* When no path-seg is configured the server-captured path-seg buffer
     * should be empty (i.e., the assembled absolute path contains no
     * additional segment between the path-prefix and the operation).
     */
    CU_ASSERT(strlen(tst_srvr_path_seg_cacerts) == 0);

    /*
     * Case B: Configure a path-seg and verify the server received that
     * exact segment as part of the assembled URI for the cacerts operation.
     */
    memset(tst_srvr_path_seg_cacerts, 0, EST_MAX_PATH_SEGMENT_LEN + 1);
    est_client_set_server(ctx, US896_SERVER_IP, US896_SERVER_PORT, path_segment);

    rc = est_client_get_cacerts(ctx, &retrieved_cacerts_len);
    CU_ASSERT(rc == EST_ERR_NONE);
    CU_ASSERT(retrieved_cacerts_len > 0);

    /* The server-captured path segment should exactly match the configured value */
    CU_ASSERT(strcmp(tst_srvr_path_seg_cacerts, path_segment) == 0);

    if (ctx) {
        est_destroy(ctx);
    }
}
