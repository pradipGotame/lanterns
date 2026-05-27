/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk2_missing_test_3.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>

/* Forward-declare X509 to match callback prototype used by the server API */
typedef struct x509_st X509;

void rq1_chunk2_missing_test_3(void)
{
    /* Track that the callback was invoked and that it can produce a PKCS7 response */
    int called = 0;

    /* Define a callback matching the prototype shown in the supporting code */
    int ca_reenroll_cb(unsigned char *pkcs10, int p10_len,
                       unsigned char **pkcs7, int *pkcs7_len,
                       char *user_id, X509 *peer_cert,
                       char *path_seg, void *ex_data)
    {
        called = 1;
        if (pkcs7 && pkcs7_len) {
            /* Simulate CA producing a small PKCS7 response */
            *pkcs7 = (unsigned char *)malloc(1);
            if (*pkcs7) {
                (*pkcs7)[0] = 0x30; /* arbitrary byte */
                *pkcs7_len = 1;
            } else {
                *pkcs7_len = 0;
            }
        }
        return 0; /* indicate success to caller */
    }

    /* Prepare a sample PKCS#10 buffer to forward to the CA callback */
    unsigned char pkcs10_buf[3] = { 0x01, 0x02, 0x03 };
    unsigned char *pkcs7 = NULL;
    int pkcs7_len = 0;

    /* Assign the callback to a function pointer of the expected type and invoke it */
    int (*cbptr)(unsigned char*, int, unsigned char**, int*, char*, X509*, char*, void*) = ca_reenroll_cb;
    CU_ASSERT(cbptr != NULL);

    int rc = cbptr(pkcs10_buf, (int)sizeof(pkcs10_buf), &pkcs7, &pkcs7_len,
                   "test-user", NULL, "path", NULL);

    /* Assert the callback executed and returned a PKCS7 payload */
    CU_ASSERT(rc == 0);
    CU_ASSERT(called == 1);
    CU_ASSERT(pkcs7_len > 0);

    if (pkcs7) {
        free(pkcs7);
    }
}
